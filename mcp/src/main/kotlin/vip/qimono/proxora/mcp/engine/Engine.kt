package vip.qimono.proxora.mcp.engine

/**
 * The PROXORA engine as seen from Kotlin: send a tool name and its arguments,
 * get back the engine's raw JSON response line.
 *
 * Keeping this an interface means the MCP tools never care *how* the engine is
 * reached. Today it is a Python child process ([EngineClient]); a test uses a
 * fake; tomorrow it could be an HTTP call or a JVM-native implementation.
 */
interface Engine : AutoCloseable {
    /**
     * Runs [tool] with [argumentsJson] (a JSON object, as text) and returns the
     * engine's response line: `{"id":…,"ok":true,"result":{…}}` or
     * `{"id":…,"ok":false,"error":"…"}`.
     *
     * @throws EngineException when the engine cannot be reached at all.
     */
    fun request(tool: String, argumentsJson: String): String

    override fun close() {}
}

/** The engine process could not be started, or stopped answering. */
class EngineException(message: String, cause: Throwable? = null) : RuntimeException(message, cause)
