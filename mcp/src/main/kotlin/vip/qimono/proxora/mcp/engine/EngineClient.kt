package vip.qimono.proxora.mcp.engine

import java.io.BufferedReader
import java.io.BufferedWriter
import java.io.IOException

/**
 * Talks to one long-lived Python engine process over line-delimited JSON.
 *
 * Starting Python with NumPy, SciPy and Qiskit takes about a second, so the
 * process is started once (lazily, on the first request) and reused. Requests
 * are serialised with a lock: one line out, one line back. If the process has
 * died, it is restarted once and the request is retried; every engine tool is
 * a pure calculation, so a retry is safe.
 *
 * Plain Kotlin standard library only, so it is easy to read and to test.
 */
class EngineClient(
    private val command: EngineCommand,
    private val extraEnvironment: Map<String, String> = emptyMap(),
) : Engine {
    private val lock = Any()
    private var process: Process? = null
    private var toEngine: BufferedWriter? = null
    private var fromEngine: BufferedReader? = null
    private var nextId = 1L

    override fun request(tool: String, argumentsJson: String): String = synchronized(lock) {
        val id = nextId++
        val line = """{"id":$id,"tool":${quote(tool)},"args":$argumentsJson}"""
        try {
            exchange(line)
        } catch (first: IOException) {
            stop()
            try {
                exchange(line)
            } catch (second: IOException) {
                stop()
                throw EngineException("The PROXORA engine is not responding: ${second.message}", second)
            }
        }
    }

    /** True while a live engine process is attached. */
    val isRunning: Boolean
        get() = synchronized(lock) { process?.isAlive == true }

    override fun close() = synchronized(lock) { stop() }

    private fun exchange(line: String): String {
        ensureStarted()
        val writer = toEngine ?: throw IOException("engine input is closed")
        val reader = fromEngine ?: throw IOException("engine output is closed")
        writer.write(line)
        writer.newLine()
        writer.flush()
        return reader.readLine() ?: throw IOException("engine closed its output (exit code ${exitCodeOrNull()})")
    }

    private fun ensureStarted() {
        if (process?.isAlive == true) return
        stop()
        val builder = ProcessBuilder(command.argv)
            // The engine's stderr (warnings, tracebacks) goes to ours: safe for MCP over stdio.
            .redirectError(ProcessBuilder.Redirect.INHERIT)
        command.workingDirectory?.let(builder::directory)
        builder.environment().putAll(extraEnvironment)
        val started = try {
            builder.start()
        } catch (problem: IOException) {
            throw EngineException("Cannot start the PROXORA engine with ${command.argv}: ${problem.message}", problem)
        }
        process = started
        toEngine = started.outputStream.bufferedWriter(Charsets.UTF_8)
        fromEngine = started.inputStream.bufferedReader(Charsets.UTF_8)
    }

    private fun stop() {
        runCatching { toEngine?.close() }
        process?.let { running ->
            if (!running.waitFor(2, java.util.concurrent.TimeUnit.SECONDS)) running.destroyForcibly()
        }
        process = null
        toEngine = null
        fromEngine = null
    }

    private fun exitCodeOrNull(): Int? = process?.let { if (it.isAlive) null else it.exitValue() }

    companion object {
        /** JSON string literal for [text]. */
        fun quote(text: String): String = buildString {
            append('"')
            for (c in text) {
                when {
                    c == '"' -> append("\\\"")
                    c == '\\' -> append("\\\\")
                    c == '\n' -> append("\\n")
                    c == '\r' -> append("\\r")
                    c == '\t' -> append("\\t")
                    c < ' ' -> append("\\u%04x".format(c.code))
                    else -> append(c)
                }
            }
            append('"')
        }
    }
}
