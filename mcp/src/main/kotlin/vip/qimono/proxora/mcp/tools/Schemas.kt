package vip.qimono.proxora.mcp.tools

import kotlinx.serialization.json.JsonObject
import kotlinx.serialization.json.JsonPrimitive
import kotlinx.serialization.json.buildJsonObject
import kotlinx.serialization.json.put
import kotlinx.serialization.json.putJsonArray

/** Small builders for the JSON Schema fragments the tools share. */
internal object Schemas {
    fun number(description: String, minimum: Double? = null, maximum: Double? = null): JsonObject = buildJsonObject {
        put("type", "number")
        put("description", description)
        minimum?.let { put("minimum", it) }
        maximum?.let { put("maximum", it) }
    }

    fun integer(description: String, minimum: Int? = null): JsonObject = buildJsonObject {
        put("type", "integer")
        put("description", description)
        minimum?.let { put("minimum", it) }
    }

    fun string(description: String, choices: List<String>, default: String? = null): JsonObject = buildJsonObject {
        put("type", "string")
        put("description", description)
        putJsonArray("enum") { choices.forEach { add(JsonPrimitive(it)) } }
        default?.let { put("default", it) }
    }

    fun arrayOf(items: JsonObject, description: String, minItems: Int? = null): JsonObject = buildJsonObject {
        put("type", "array")
        put("description", description)
        put("items", items)
        minItems?.let { put("minItems", it) }
    }

    fun obj(properties: Map<String, JsonObject>, required: List<String>, description: String): JsonObject =
        buildJsonObject {
            put("type", "object")
            put("description", description)
            put("properties", JsonObject(properties))
            putJsonArray("required") { required.forEach { add(JsonPrimitive(it)) } }
        }
}
