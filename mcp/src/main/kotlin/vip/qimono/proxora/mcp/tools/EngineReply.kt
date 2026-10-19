package vip.qimono.proxora.mcp.tools

import io.modelcontextprotocol.kotlin.sdk.types.CallToolResult
import io.modelcontextprotocol.kotlin.sdk.types.TextContent
import kotlinx.serialization.SerializationException
import kotlinx.serialization.json.Json
import kotlinx.serialization.json.JsonElement
import kotlinx.serialization.json.JsonObject
import kotlinx.serialization.json.booleanOrNull
import kotlinx.serialization.json.contentOrNull
import kotlinx.serialization.json.jsonObject
import kotlinx.serialization.json.jsonPrimitive

/** What the engine answered: a result, or an error message. */
sealed interface EngineReply {
    data class Success(val result: JsonObject) : EngineReply

    data class Failure(val error: String) : EngineReply

    /** The same reply as an MCP tool result: readable text plus structured JSON. */
    fun toCallToolResult(): CallToolResult = when (this) {
        is Success -> CallToolResult(
            content = listOf(TextContent(pretty.encodeToString(JsonElement.serializer(), result))),
            structuredContent = result,
        )
        is Failure -> CallToolResult(content = listOf(TextContent(error)), isError = true)
    }

    companion object {
        private val pretty = Json { prettyPrint = true }

        /** Parses one engine response line: `{"ok": true, "result": {…}}` or `{"ok": false, "error": "…"}`. */
        fun parse(line: String): EngineReply {
            val reply = try {
                Json.parseToJsonElement(line).jsonObject
            } catch (problem: SerializationException) {
                return Failure("The engine sent an unreadable reply: ${problem.message}")
            } catch (problem: IllegalArgumentException) {
                return Failure("The engine sent an unreadable reply: ${problem.message}")
            }
            val ok = reply["ok"]?.jsonPrimitive?.booleanOrNull ?: false
            if (!ok) {
                return Failure(reply["error"]?.jsonPrimitive?.contentOrNull ?: "The engine reported an unknown error.")
            }
            val result = reply["result"] as? JsonObject
                ?: return Failure("The engine reply has no result object.")
            return Success(result)
        }
    }
}
