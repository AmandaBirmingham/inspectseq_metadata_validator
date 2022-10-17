import json
import yaml
from great_expectations.render.types import RenderedTableContent, RenderedBulletListContent, RenderedGraphContent

from typing import Any, Callable, Dict, List, Optional, Union

from numpy import array

from great_expectations.execution_engine import (
    PandasExecutionEngine,
)
from great_expectations.execution_engine.execution_engine import (
    ExecutionEngine,
    MetricDomainTypes,
    MetricPartialFunctionTypes,
)
from great_expectations.expectations.expectation import (
    ColumnMapExpectation,
    ExpectationConfiguration,
    ExpectationValidationResult,
)
from great_expectations.expectations.metrics import (
    ColumnMapMetricProvider,
    column_condition_partial,
    metric_partial,
)
from great_expectations.expectations.metrics.import_manager import F, sa
from great_expectations.expectations.util import render_evaluation_parameter_string
from great_expectations.render.renderer.renderer import renderer
from great_expectations.render.types import (
    CollapseContent,
    RenderedStringTemplateContent,
)
from great_expectations.render.util import (
    handle_strict_min_max,
    parse_row_condition_string_pandas_engine,
    substitute_none_for_missing,
)
from great_expectations.validator.metric_configuration import MetricConfiguration


def _test_cell_value(cell_value, allowed_locations):
    delimiter = "/"
    if type(cell_value) == str:
        cell_value = cell_value.rstrip(delimiter)
        # split each column value on /
        pieces = cell_value.split(delimiter)
        curr_dict = allowed_locations

        for curr_piece in pieces:
            curr_dict = curr_dict.get(curr_piece, None)
            if curr_dict is None:
                return False

    return True


# This class defines a Metric to support your Expectation.
# For most ColumnMapExpectations, the main business logic for calculation will live in this class.
class ColumnValuesParseIntoExpectedLocations(ColumnMapMetricProvider):

    # This is the id string that will be used to reference your metric.
    condition_metric_name = "column_values.parse_into_expected_locations"
    allowed_locations = None

    @classmethod
    def _load_allowed_location(cls, allowed_locations_abs_fp):
        locations_dict = allowed_locations_abs_fp
        if not type(allowed_locations_abs_fp) == dict:
            with open(allowed_locations_abs_fp, 'r') as file:
                locations_dict = yaml.load(file, Loader=yaml.FullLoader)
        cls.allowed_locations = locations_dict

    condition_value_keys = ("allowed_locations_abs_fp",)

    # This method implements the core logic for the PandasExecutionEngine
    @column_condition_partial(engine=PandasExecutionEngine)
    def _pandas(cls, column, allowed_locations_abs_fp, **kwargs):
        cls._load_allowed_location(allowed_locations_abs_fp)
        return column.apply(_test_cell_value, args=(cls.allowed_locations,))

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
class ExpectColumnValuesToParseIntoExpectedLocations(ColumnMapExpectation):
    """Expect values in this column to parse into pieces corresponding to an expected location."""

    _allowed_locations = {
                               "North America": {
                                   "USA": {
                                       "California": {"San Diego": {}},
                                       "Nevada": {"Clark County": {}},
                                       "Alabama": {"Birmingham": {}},
                                       "Michigan": {}
                                   },
                                   "Mexico": {
                                       "Tijuana": {}
                                   }
                               }
                           }

    # These examples will be shown in the public gallery.
    # They will also be executed as unit tests for your Expectation.
    examples = [
        {
            "data": {
                "all_known_locations": ["North America/USA/California/San Diego",
                                        "North America/USA/Michigan/",
                                        "North America/Mexico/Tijuana",
                                        "North America/USA/Nevada/Clark County",
                                        "North America/USA/Alabama/Birmingham"],
                "some_unknown_locations": ["North Ameerica/USA/California/San Diego",
                                           "North America/USA/Califorenia/San Diego",
                                           "North America/USA/California/San Diego",
                                           "North America/Mexico/Tijuana",
                                           "North America/USA/Nevada/ Clark County"],
            },
            "tests": [
                {
                    "title": "basic_positive_test",
                    "exact_match_out": False,
                    "include_in_gallery": True,
                    "in": {"column": "all_known_locations",
                           "allowed_locations_abs_fp": _allowed_locations
                           },
                           "out": {
                        "success": True,
                    },
                },
                {
                    "title": "basic_negative_test",
                    "exact_match_out": False,
                    "include_in_gallery": True,
                    "in": {"column": "some_unknown_locations",
                           "allowed_locations_abs_fp": _allowed_locations
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
    map_metric = "column_values.parse_into_expected_locations"

    # This is a list of parameter names that can affect whether the Expectation evaluates to True or False
    # Please see https://docs.greatexpectations.io/en/latest/reference/core_concepts/expectations/expectations.html#expectation-concepts-domain-and-success-keys
    # for more information about domain and success keys, and other arguments to Expectations
    success_keys = ("mostly", "allowed_locations_abs_fp")

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
        template_str = "must contain only one of the allowed locations."

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
    ExpectColumnValuesToParseIntoExpectedLocations().print_diagnostic_checklist()

# Note to users: code below this line is only for integration testing -- ignore!

diagnostics = ExpectColumnValuesToParseIntoExpectedLocations().run_diagnostics()
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
