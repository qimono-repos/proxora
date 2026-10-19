package vip.qimono.proxora.mcp.tools

import io.modelcontextprotocol.kotlin.sdk.types.ToolSchema
import kotlinx.serialization.json.buildJsonObject
import kotlinx.serialization.json.put

/** Walk-forward comparison of the predictors on one series. */
class BacktestTool : ProxoraTool(
    name = "backtest",
    description = """
        Walk-forward test on one series: at each step, train on the past, predict the next value
        and score it. Returns a summary (MSPE, RMSPE, hit rate, ...) and the scored steps for each
        method, so 'lr' and 'qu' are compared on the same data. No quantum advantage is assumed.
    """.trimIndent(),
) {
    override val inputSchema = ToolSchema(
        properties = buildJsonObject {
            put("values", Schemas.arrayOf(Schemas.number("A value of the series."), "The series, oldest first."))
            put(
                "methods",
                Schemas.arrayOf(
                    Schemas.string("A method.", listOf("lr", "qu")),
                    "Methods to compare. Default: both.",
                ),
            )
            put("min_train", Schemas.integer("Values used before the first prediction. Default 6.", minimum = 3))
            put("confidence", Schemas.number("Confidence level of the ranges, e.g. 0.9.", minimum = 0.5, maximum = 0.999))
        },
        required = listOf("values"),
    )
}
