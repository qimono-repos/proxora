package vip.qimono.proxora.mcp.tools

import io.modelcontextprotocol.kotlin.sdk.types.CallToolResult
import io.modelcontextprotocol.kotlin.sdk.types.TextContent
import io.modelcontextprotocol.kotlin.sdk.types.ToolAnnotations
import io.modelcontextprotocol.kotlin.sdk.types.ToolSchema
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import kotlinx.serialization.json.JsonObject
import vip.qimono.proxora.mcp.engine.Engine
import vip.qimono.proxora.mcp.engine.EngineException

/**
 * One MCP tool backed by the PROXORA engine.
 *
 * A subclass only describes itself: its [name], [description] and
 * [inputSchema]. The shared behaviour lives here once: check required
 * arguments, forward the call to the engine off the coroutine's thread, and
 * turn the engine's reply into an MCP [CallToolResult].
 */
abstract class ProxoraTool(
    val name: String,
    val description: String,
) {
    /** JSON Schema of the arguments, shown to the model that calls the tool. */
    abstract val inputSchema: ToolSchema

    /** Every PROXORA tool is a pure calculation: read-only, repeatable, offline. */
    open val annotations: ToolAnnotations =
        ToolAnnotations(readOnlyHint = true, idempotentHint = true, openWorldHint = false)

    /** Runs the tool. Never throws: problems come back as an error result. */
    suspend fun call(engine: Engine, arguments: JsonObject?): CallToolResult {
        val args = arguments ?: JsonObject(emptyMap())
        val missing = inputSchema.required.orEmpty().filterNot { it in args }
        if (missing.isNotEmpty()) {
            return errorResult("Missing required argument(s): ${missing.joinToString()}.")
        }
        val reply = try {
            // The engine call blocks on a pipe, so keep it off the coroutine's thread.
            withContext(Dispatchers.IO) { engine.request(name, args.toString()) }
        } catch (problem: EngineException) {
            return errorResult(problem.message ?: "The PROXORA engine is unavailable.")
        }
        return EngineReply.parse(reply).toCallToolResult()
    }

    protected fun errorResult(message: String): CallToolResult =
        CallToolResult(content = listOf(TextContent(message)), isError = true)
}
