package vip.qimono.proxora.mcp.engine

import java.io.File

/**
 * How to start the Python engine bridge (`python -m proxora.bridge`).
 *
 * Resolution order:
 * 1. `PROXORA_ENGINE_CMD`: the full command, split on spaces
 *    (e.g. `python3 -m proxora.bridge`, with `PYTHONPATH` set by you).
 * 2. `PROXORA_ENGINE_DIR`: the engine's `python/` folder, run through uv:
 *    `uv run --quiet --directory <dir> python -m proxora.bridge`.
 * 3. Otherwise the repo layout is assumed: `../python` when started from `mcp/`,
 *    or `python` when started from the repository root.
 */
data class EngineCommand(val argv: List<String>, val workingDirectory: File? = null) {
    init {
        require(argv.isNotEmpty()) { "The engine command is empty." }
    }

    companion object {
        private val BRIDGE = listOf("python", "-m", "proxora.bridge")

        fun fromEnvironment(
            env: Map<String, String> = System.getenv(),
            currentDirectory: File = File(System.getProperty("user.dir")),
        ): EngineCommand {
            env["PROXORA_ENGINE_CMD"]?.trim()?.takeIf { it.isNotEmpty() }?.let { raw ->
                return EngineCommand(raw.split(Regex("\\s+")))
            }
            val engineDir = env["PROXORA_ENGINE_DIR"]?.let(::File)
                ?: listOf(File(currentDirectory, "../python"), File(currentDirectory, "python"))
                    .firstOrNull { File(it, "src/proxora/bridge.py").isFile }
                ?: throw EngineException(
                    "Cannot find the PROXORA engine. Set PROXORA_ENGINE_DIR to the repo's python/ folder " +
                        "or PROXORA_ENGINE_CMD to a full command.",
                )
            return uvRun(engineDir.canonicalFile)
        }

        fun uvRun(engineDir: File): EngineCommand =
            EngineCommand(listOf("uv", "run", "--quiet", "--directory", engineDir.path) + BRIDGE)
    }
}
