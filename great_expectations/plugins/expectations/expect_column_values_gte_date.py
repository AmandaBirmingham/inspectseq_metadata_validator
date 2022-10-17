from datetime import timezone, datetime
from dateutil.parser import parse

from great_expectations.render.types import RenderedTableContent, RenderedBulletListContent, RenderedGraphContent

from typing import Any, Dict, List, Optional, Union

from great_expectations.execution_engine import (
    PandasExecutionEngine,
)
from great_expectations.execution_engine.execution_engine import (
    ExecutionEngine,
)
from great_expectations.expectations.expectation import (
    ColumnMapExpectation,
    ExpectationConfiguration,
    ExpectationValidationResult,
)
from great_expectations.expectations.metrics import (
    ColumnMapMetricProvider,
    column_condition_partial,
)
from great_expectations.expectations.util import render_evaluation_parameter_string
from great_expectations.render.renderer.renderer import renderer
from great_expectations.render.types import (
    RenderedStringTemplateContent,
)
from great_expectations.render.util import (
    parse_row_condition_string_pandas_engine,
    substitute_none_for_missing,
)
from great_expectations.validator.metric_configuration import MetricConfiguration


# This class defines a Metric to support your Expectation.
# For most ColumnMapExpectations, the main business logic for calculation will live in this class.
class ColumnValuesCompareToDate(ColumnMapMetricProvider):
    condition_metric_name = "column_values.date_gte"
    condition_value_keys = (
        "min_value",
    )

    @column_condition_partial(engine=PandasExecutionEngine)
    def _pandas(
        cls,
        column,
        min_value,
        dates_have_tz=True,
        **kwargs
    ):
        try:
            compare_date = datetime.strptime(min_value, "%Y-%m-%d %H:%M:%S")
        except ValueError as ex:
            compare_date = datetime.fromisoformat(min_value)
        if dates_have_tz and compare_date.tzinfo is None:
            compare_date = compare_date.replace(tzinfo=timezone.utc)
        temp_column = column.map(parse)
        return temp_column >= compare_date

    @classmethod
    def _get_evaluation_dependencies(
        cls,
        metric: MetricConfiguration,
        configuration: Optional[ExpectationConfiguration] = None,
        execution_engine: Optional[ExecutionEngine] = None,
        runtime_configuration: Optional[Dict] = None,
    ):
        """Returns a dictionary of given metric names and their corresponding configuration, specifying the metric
        types and their respective domains"""
        dependencies: Dict = super()._get_evaluation_dependencies(
            metric=metric,
            configuration=configuration,
            execution_engine=execution_engine,
            runtime_configuration=runtime_configuration,
        )

        table_domain_kwargs: Dict = {
            k: v for k, v in metric.metric_domain_kwargs.items() if k != "column"
        }
        dependencies["table.column_types"] = MetricConfiguration(
            metric_name="table.column_types",
            metric_domain_kwargs=table_domain_kwargs,
            metric_value_kwargs={
                "include_nested": True,
            },
            metric_dependencies=None,
        )

        return dependencies


# This class defines the Expectation itself
class ExpectColumnValuesGteDate(ColumnMapExpectation):
    """Expect values in this column to be timezone-aware dates greater than or equal to an input date."""

    # These examples will be shown in the public gallery.
    # They will also be executed as unit tests for your Expectation.
    examples = [
        {
            "data": {
                "good_dates": ["2021-01-14 14:07:46.878991+00:00",
                               "2019-12-22 00:00:00+00:00"],
                "bad_dates": ["2018-01-14 14:07:46.878991+00:00",
                               "2007-12-22 00:00:00+00:00"],
            },
            "tests": [
                {
                    "title": "basic_positive_test",
                    "exact_match_out": False,
                    "include_in_gallery": True,
                    "in": {"column": "good_dates",
                           "min_value": "2019-01-01 00:00:00"
                           },
                           "out": {
                        "success": True,
                    },
                },
                {
                    "title": "basic_negative_test",
                    "exact_match_out": False,
                    "include_in_gallery": True,
                    "in": {"column": "bad_dates",
                           "min_value": "2019-01-01 00:00:00"
                           },
                    "out": {
                        "success": False,
                    },
                },
            ],
        }
    ]

    # This is the id string of the Metric used by this Expectation.
    # For most Expectations, it will be the same as the `condition_metric_name` defined in your Metric class above.
    map_metric = "column_values.date_gte"

    # This is a list of parameter names that can affect whether the Expectation evaluates to True or False
    # Please see https://docs.greatexpectations.io/en/latest/reference/core_concepts/expectations/expectations.html#expectation-concepts-domain-and-success-keys
    # for more information about domain and success keys, and other arguments to Expectations
    success_keys = ("mostly", "min_value", "dates_have_tz")

    # This dictionary contains default values for any parameters that should have default values
    default_kwarg_values = {}

    @classmethod
    @renderer(renderer_type="renderer.prescriptive")
    @render_evaluation_parameter_string
    def _prescriptive_renderer(
            cls,
            configuration: ExpectationConfiguration = None,
            result: ExpectationValidationResult = None,
            language: str = None,
            runtime_configuration: dict = None,
            **kwargs,
    ) -> List[Union[dict, str, RenderedStringTemplateContent, RenderedTableContent, RenderedBulletListContent,
                    RenderedGraphContent, Any]]:
        runtime_configuration = runtime_configuration or {}
        include_column_name = runtime_configuration.get("include_column_name", True)
        include_column_name = (
            include_column_name if include_column_name is not None else True
        )
        styling = runtime_configuration.get("styling")
        # get params dict with all expected kwargs
        params = substitute_none_for_missing(
            configuration.kwargs,
            [
                "column",
                "row_condition",
                "condition_parser",
            ],
        )

        # build string template
        template_str = "must be greater than or equal to input date"

        if include_column_name:
            template_str = "$column " + template_str

        if params["row_condition"] is not None:
            (
                conditional_template_str,
                conditional_params,
            ) = parse_row_condition_string_pandas_engine(params["row_condition"])
            template_str = conditional_template_str + ", then " + template_str
            params.update(conditional_params)

        # return simple string
        return [
            RenderedStringTemplateContent(
                **{
                    "content_block_type": "string_template",
                    "string_template": {
                        "template": template_str,
                        "params": params,
                        "styling": styling,
                    },
                }
            )
        ]

    # This dictionary contains metadata for display in the public gallery
    library_metadata = {
        "tags": ["extremely basic math"],
        "contributors": ["@joegargery"],
    }


if __name__ == "__main__":
    ExpectColumnValuesGteDate().print_diagnostic_checklist()

# Note to users: code below this line is only for integration testing -- ignore!

# diagnostics = ExpectColumnValuesGteDate().run_diagnostics()
#
# for check in diagnostics["tests"]:
#     assert check["test_passed"] is True
#     assert check["error_message"] is None
#     assert check["stack_trace"] is None
#
# for check in diagnostics["errors"]:
#     assert check is None

#for check in diagnostics["maturity_checklist"]["experimental"]:
#    assert check["passed"] is True