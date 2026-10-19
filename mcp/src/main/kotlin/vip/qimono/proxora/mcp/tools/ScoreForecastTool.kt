package vip.qimono.proxora.mcp.tools

import io.modelcontextprotocol.kotlin.sdk.types.ToolSchema
import kotlinx.serialization.json.buildJsonObject
import kotlinx.serialization.json.put

/** One forecast against the value that was later observed. */
class ScoreForecastTool : ProxoraTool(
    name = "score_forecast",
    description = """
        Score one forecast against the observed value. Returns the residual (actual − forecast),
        absolute and squared error, percentage error and SPE = ((actual − forecast) / actual)².
        With a range [low, high] it also returns whether the actual landed inside it and the
        epsilon-tube loss (distance outside the range; 0 inside it, as in support vector regression).
    """.trimIndent(),
) {
    override val inputSchema = ToolSchema(
        properties = buildJsonObject {
            put("actual", Schemas.number("Observed value at the forecast target time."))
            put("forecast", Schemas.number("The forecast point value."))
            put("low", Schemas.number("Lower edge of the forecast range. Give with high, or omit both."))
            put("high", Schemas.number("Upper edge of the forecast range. Give with low, or omit both."))
        },
        required = listOf("actual", "forecast"),
    )
}
