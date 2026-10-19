package vip.qimono.proxora.mcp.tools

import io.modelcontextprotocol.kotlin.sdk.types.ToolSchema
import kotlinx.serialization.json.buildJsonObject
import kotlinx.serialization.json.put

/** Many forecasts at once, with summaries that compare across assets. */
class ScoreBatchTool : ProxoraTool(
    name = "score_batch",
    description = """
        Score many forecasts at once. Returns per-row scores, an overall summary (MSPE, RMSPE,
        MAPE, hit rate, mean epsilon loss) and a per-asset summary that also includes MSE in the
        asset's own price units. MSPE/RMSPE are comparable across assets of any price.
    """.trimIndent(),
) {
    private val record = Schemas.obj(
        properties = mapOf(
            "actual" to Schemas.number("Observed value at the forecast target time."),
            "forecast" to Schemas.number("The forecast point value."),
            "low" to Schemas.number("Lower edge of the forecast range (optional)."),
            "high" to Schemas.number("Upper edge of the forecast range (optional)."),
            "asset" to buildJsonObject {
                put("type", "string")
                put("description", "Asset or lot label, e.g. 'TSLAB'.")
            },
        ),
        required = listOf("actual", "forecast"),
        description = "One logged forecast and the value that was later observed.",
    )

    override val inputSchema = ToolSchema(
        properties = buildJsonObject {
            put("records", Schemas.arrayOf(record, "The forecasts to score.", minItems = 1))
        },
        required = listOf("records"),
    )
}
