from copy import deepcopy
from typing import Dict, Tuple, Any, Optional, Callable, List

from great_expectations.core import ExpectationConfiguration
from great_expectations.execution_engine import (
    ExecutionEngine
)
from great_expectations.expectations.expectation import TableExpectation
from great_expectations.exceptions.exceptions import InvalidExpectationKwargsError


class ExpectTableColumnsNotUnnamed(TableExpectation):
    """Expect the columns not to contain more than an input number of unnamed columns"""

    metric_dependencies = ("table.columns",)
    success_keys = (
        "exception_num",
    )
    default_kwarg_values = {
        "exception_num": 0,
        "result_format": "BASIC",
        "include_config": True,
        "catch_exceptions": False,
    }
    args_keys = (
        "exception_num",
    )

    @staticmethod
    def _validate_success_key(
        param: str,
        required: bool,
        configuration: Optional[ExpectationConfiguration],
        validation_rules: Dict[Callable, str],
    ) -> None:
        """Simple method to aggregate and apply validation rules to the `param`."""
        if param not in configuration.kwargs:
            if required:
                raise InvalidExpectationKwargsError(
                    f"Param {param} is required but was not found in configuration."
                )
            return

        param_value = configuration.kwargs[param]

        for rule, error_message in validation_rules.items():
            if not rule(param_value):
                raise InvalidExpectationKwargsError(error_message)

    def validate_configuration(
        self, configuration: Optional[ExpectationConfiguration]
    ) -> bool:
        super().validate_configuration(configuration=configuration)
        if configuration is None:
            configuration = self.configuration

        self._validate_success_key(
            param="exception_num",
            required=False,
            configuration=configuration,
            validation_rules={
                lambda x: isinstance(x, int): "exception_num should be a int.",
                lambda x: int(x)>=0: "exception_num should be >= 0",
            },
        )

        return True

    def _validate(
        self,
        configuration: ExpectationConfiguration,
        metrics: Dict,
        runtime_configuration: dict = None,
        execution_engine: ExecutionEngine = None,
    ) -> Dict:
        exception_num = self.get_success_kwargs(configuration).get("exception_num")
        actual_column_list = metrics.get("table.columns")
        unnamed_cols = [x for x in actual_column_list if x.startswith("Unnamed")]
        if len(unnamed_cols) <= int(exception_num):
            return {"success": True, "result": {"observed_value": actual_column_list}}
        else:
            # Convert to lists and sort to lock order for testing and output rendering
            # unexpected_list contains items from the dataset columns that are not in expected_column_set
            unexpected_list = sorted(unnamed_cols)[exception_num:]
            # observed_value contains items that are in the dataset columns
            observed_value = sorted(actual_column_list)

            mismatched = {}
            if len(unexpected_list) > 0:
                mismatched["unexpected"] = unexpected_list

            return_failed = {
                "success": False,
                "result": {
                    "observed_value": observed_value,
                    "details": {"mismatched": mismatched},
                },
            }

            return return_failed
