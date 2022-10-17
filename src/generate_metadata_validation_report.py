import pathlib
import pandas
import great_expectations as ge
from sys import argv
from datetime import datetime

DEFAULT_FAIL_EXPECT_SUITE_NAME = "inspectseq_metadata_failure_draft10"
DEFAULT_WARN_EXPECT_SUITE_NAME = "inspectseq_metadata_warning_draft5"
DATASOURCE_NAME = "inspectseq_metadata"
METADATA_CLEARED = "metadata_cleared"
NOT_BAD_KIND = "not_known_bad"
FULL_REPORT_FNAME_ROOT = "_validation_report_"

# NB: ensure DIFF_REPORT_FNAME_ROOT is not substring of FULL_REPORT_FNAME_ROOT
DIFF_REPORT_FNAME_ROOT = "_validation_differential_report_"
SEARCH_ID_COL_NAME = "search_id"
FAIL_SOURCE_COL_NAME = "fail_source"
FAIL_COL_NAME = "fail_column"
FAIL_VAL_COL_NAME = "fail_value"
FAIL_CHECK_COL_NAME = "fail_check"
FAIL_TYPE_COL_NAME = "fail_type"


def _validate_datacontext(context, datasource_name, expectation_suite_name,
                          default_data_name, inspectseq_df):
    batch_request = {
        "datasource_name": datasource_name,
        "data_connector_name": "default_runtime_data_connector_name",
        "data_asset_name": default_data_name
    }

    checkpoint_config = {
        "name": "input_df_checkpoint",
        "class_name": "SimpleCheckpoint",
        "validations": [
            {
                "batch_request": batch_request,
                "expectation_suite_name": expectation_suite_name
            }
        ],
        "runtime_configuration": {
            "result_format": {
                "result_format": "COMPLETE",
                "include_unexpected_rows": True,
            }
        }
    }

    context.add_checkpoint(**checkpoint_config)

    # switched over to passing in a dataframe rather than letting great
    # expectations load the csv into a dataframe behind the scenes in order
    # to prevent GE/pandas from automagically converting zip codes to floating-
    # point numbers--sheesh.
    checkpoint_result = context.run_checkpoint(
        checkpoint_name="input_df_checkpoint",
        batch_request={
            "runtime_parameters": {"batch_data": inspectseq_df},
            "batch_identifiers": {
                "default_identifier_name": default_data_name
            },
        },
    )

    return checkpoint_result


def _generate_validation_fail_df(context, datasource_name, checkpoint_result,
                                 expectation_suite_type):
    a_dataframe = context.datasources[
        datasource_name].execution_engine.active_batch_data.dataframe
    search_id_col_idx = a_dataframe.columns.get_loc(SEARCH_ID_COL_NAME)

    validation_result_id = \
        checkpoint_result.list_validation_result_identifiers()[0]
    results = checkpoint_result.run_results[
        validation_result_id]["validation_result"].results

    fail_df = None
    for curr_result in results:
        if not curr_result.success:
            if curr_result.exception_info and \
                    curr_result.exception_info['raised_exception']:
                print(f"Validation failed: {curr_result.exception_info}")
                continue

            fail_type = curr_result.expectation_config.expectation_type
            if 'unexpected_index_list' in curr_result.result:
                fail_column = curr_result.expectation_config.kwargs["column"]
                fail_indices = curr_result.result['unexpected_index_list']
                fail_values = curr_result.result["unexpected_list"]
                fail_cols = [fail_column for i in range(len(fail_values))]
                curr_fail_df = a_dataframe.iloc[fail_indices,
                                                [search_id_col_idx]].copy()
                curr_fail_df.rename(
                    columns={SEARCH_ID_COL_NAME: FAIL_SOURCE_COL_NAME},
                    inplace=True)
            elif "details" in curr_result.result and "mismatched" in \
                    curr_result.result["details"]:
                fail_info = curr_result.result["details"]["mismatched"]
                fail_key = "missing" if "missing" in fail_info \
                    else "unexpected"
                fail_cols = fail_info[fail_key]
                fail_values = [fail_key for i in range(len(fail_cols))]
                curr_fail_df = pandas.DataFrame(
                    {FAIL_SOURCE_COL_NAME: ["column" for i in
                                            range(len(fail_values))]})
            else:
                raise ValueError(f"unrecognized outputs for expectation "
                                 f"{fail_type}")

            curr_fail_df[FAIL_COL_NAME] = fail_cols
            # force the fail values to be recorded as strings, since otherwise
            # if they are all numbers, pandas coerces them to numeric, which
            # then makes for issues comparing to any previous failure report
            # where NOT all the fail values were numeric and thus the column
            # was stored as a string :-|
            curr_fail_df[FAIL_VAL_COL_NAME] = [str(i) for i in fail_values]
            curr_fail_df[FAIL_CHECK_COL_NAME] = [fail_type for i in
                                                 range(len(fail_values))]
            curr_fail_df[FAIL_TYPE_COL_NAME] = [expectation_suite_type for
                                                i in range(len(fail_values))]

            if fail_df is None:
                fail_df = curr_fail_df.copy()
            else:
                fail_df = pandas.concat([fail_df, curr_fail_df])

    return fail_df


def generate_full_validation_df(context, expectation_suite_name,
                                expectation_type, run_name, inspectseq_df):
    a_checkpoint_result = _validate_datacontext(
        context, DATASOURCE_NAME, expectation_suite_name, run_name,
        inspectseq_df)
    validation_fail_df = _generate_validation_fail_df(
        context, DATASOURCE_NAME, a_checkpoint_result, expectation_type)
    return validation_fail_df


def _get_latest_validation_report(report_path, df_kind=""):
    latest_report_fp = None
    full_report_fps = list(report_path.glob(
        f"*{FULL_REPORT_FNAME_ROOT}{df_kind}*"))
    if len(full_report_fps) > 0:
        latest_report_fp = max(full_report_fps,
                               key=lambda item: item.stat().st_ctime)
    return latest_report_fp


def generate_differential_validation_df(latest_report_file, current_report_df):
    merge_col_name = "_merge"
    latest_report_df = pandas.read_csv(latest_report_file,
                                       na_values='', keep_default_na=False)
    merged_df = current_report_df.merge(
        latest_report_df.drop_duplicates(),
        on=[FAIL_SOURCE_COL_NAME, FAIL_COL_NAME, FAIL_VAL_COL_NAME,
            FAIL_CHECK_COL_NAME, FAIL_TYPE_COL_NAME],
        how='left', indicator=True)
    new_records_mask = merged_df[merge_col_name] == 'left_only'
    differential_df = merged_df[new_records_mask].copy()
    differential_df = differential_df.drop(merge_col_name, axis=1)   # 1 = cols
    return differential_df


def _save_report_file(df_kind, report_df, report_type, output_path):
    if report_df is not None and len(report_df) > 0:
        report_df.to_csv(output_path.absolute(), index=False)
        print(f"{report_type} {df_kind} detected and report saved")
    else:
        # create an empty file as a sentinel
        output_path.touch()
        print(f"No {report_type} {df_kind} detected")


def generate_failure_and_warning_reports(arg_list):
    inspectseq_csv_fp = arg_list[1]
    failure_expectation_suite_name = arg_list[2] if len(arg_list) == 3 else \
        DEFAULT_FAIL_EXPECT_SUITE_NAME
    warning_expectation_suite_name = arg_list[3] if len(arg_list) == 4 else \
        DEFAULT_WARN_EXPECT_SUITE_NAME

    inspectseq_csv_path = pathlib.Path(inspectseq_csv_fp)
    curr_datetime = datetime.now()
    curr_datetime_str = curr_datetime.strftime('%Y-%m-%d_%H-%M-%S')

    def _get_report_path(report_name_root, df_kind):
        if df_kind != "":
            df_kind = df_kind + "_"
        fname = f"{inspectseq_csv_path.stem}{report_name_root}" \
                f"{df_kind}{curr_datetime_str}.csv"
        return inspectseq_csv_path.parent / fname

    context = ge.data_context.DataContext()

    # IDE marks these imports as not installed, but this appears to be a
    # quirk of Great Expectations: they become installed ONLY AFTER the
    # DataContext is instantiated--which is why they have to be imported here
    # rather than at the top of the module as usual
    from expectations.expect_column_values_gte_date import \
        ExpectColumnValuesGteDate
    from expectations.expect_column_values_lte_date import \
        ExpectColumnValuesLteDate
    from expectations.expect_table_columns_not_unnamed import \
        ExpectTableColumnsNotUnnamed
    from expectations.expect_column_values_to_parse_into_expected_locations \
        import ExpectColumnValuesToParseIntoExpectedLocations
    from expectations.expect_column_values_are_unique import \
        ExpectColumnValuesAreUnique

    inspectseq_path_str = str(inspectseq_csv_path.absolute())
    inspectseq_df = pandas.read_csv(inspectseq_path_str, dtype={"zip": str})

    # NB: if sample's metadata_cleared is NA, sample is not known bad.
    # This is because we have no knowledge about whether that metadata is bad.
    known_bad = inspectseq_df[METADATA_CLEARED] == False  # noqa 712
    inspectseq_not_known_bad_df = inspectseq_df[~known_bad].copy()
    inspectseq_not_known_bad_df.reset_index(inplace=True, drop=True)

    def _generate_report_pair(df_kind, a_df):
        run_name = f"{inspectseq_csv_path.stem}_{df_kind}_{curr_datetime_str}"
        full_fail_report_df = generate_full_validation_df(
            context, failure_expectation_suite_name, "failure", run_name, a_df)
        full_warn_report_df = generate_full_validation_df(
            context, warning_expectation_suite_name, "warning", run_name, a_df)
        full_report_df = pandas.concat(
            [full_fail_report_df, full_warn_report_df], ignore_index=True)

        # Important: DO NOT SAVE full report df to a file BEFORE
        # running differential report!
        latest_report_fp = _get_latest_validation_report(
            inspectseq_csv_path.parent, df_kind)
        if full_report_df is not None:
            if latest_report_fp is None:
                print(f"No previous {df_kind} validation report available so "
                      f"no differential report created")
            else:
                diff_report_path = _get_report_path(
                    DIFF_REPORT_FNAME_ROOT, df_kind)
                diff_report_df = generate_differential_validation_df(
                    latest_report_fp, full_report_df)
                _save_report_file(
                    df_kind, diff_report_df, f"Differential validation issues",
                    diff_report_path)

        full_report_path = _get_report_path(FULL_REPORT_FNAME_ROOT, df_kind)
        _save_report_file(df_kind, full_report_df, f"Validation issues",
                          full_report_path)

    _generate_report_pair("", inspectseq_df)
    _generate_report_pair(NOT_BAD_KIND, inspectseq_not_known_bad_df)


def main():
    generate_failure_and_warning_reports(argv)


if __name__ == '__main__':
    # example call:
    # generate_metadata_reports \
    #   /Users/me/Desktop/covid_temp/all_samples_search_ids_20220419.csv

    main()
