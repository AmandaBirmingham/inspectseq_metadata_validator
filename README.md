# InspectSeq Metadata Validator

## Introduction

The purpose of this validator is to examine an InspectSeq metadata csv
file created for input to the [C-VIEW](https://github.com/ucsd-ccbb/C-VIEW) pipeline 
and generate a report on whether it contains any known metadata flaws. It reports both validation failures (known unacceptable metadata values) as well
as validation warnings (metadata values that *often but not always* represent a
metadata flaw and require human examination to disambiguate). The validator is
built on the [Great Expectations](https://greatexpectations.io/) software package.

## Validator Reports

On each run, the validator produces a minimum of two reports:
   * The `*_validation_report_*.csv` contains a report of failures and warnings for ALL records in the metadata file  
   * The `*_validation_report_not_known_bad_*.csv` contains a report of failures and warnings for records in the metadata file that do not already have their `metadata_cleared` field set to False

Report names are prefixed with the name of the metadata file that was validated 
and suffixed with the timestamp on which they were run, with the report type 
specified in between.  For example, the report named 
`all_samples_search_ids_20221006_validation_differential_report_2022-10-17_10-26-47` 
was run on metadata file `all_samples_search_ids_20221006.csv` on 2022-10-17 at 10:26:47.

Often it is useful to see what new validation issues have emerged since the last 
metadata file was produced.  If the new metadata file is placed in the same directory
as the reports produced on the previous metadata file, then the validator will also 
automatically produce two "differential" reports:
   * The `*_validation_differential_report_*.csv` contains a report of failures and warnings that were not included in the previous report, for ALL records in the metadata file  
   * The `*_validation_differential_report_not_known_bad_*.csv` contains a report of failures and warnings that were not included in the previous report, for records in the metadata file that do not already have their `metadata_cleared` field set to False

Note that, if NO failures or warnings are found for a particular report type, 
an *empty* file with the appropriate report name will be created.  This shows that
this report was run and found no problems, rather than being accidentally skipped.

A report contains five columns, as shown in the example below:

| fail_source  | fail_column | fail_value | fail_check                         | fail_type |
|--------------|-------------|------------|------------------------------------|-----------|
| SEARCH-78921 | subject_age | -6         | expect_column_values_to_be_between | failure   |
| SEARCH-89931 | subject_age | -7         | expect_column_values_to_be_between | failure   |
| SEARCH-32766 | sample_collection_datetime | 2012-05-12 08:10:00+00:00        | expect_column_values_gte_date | warning   |
| SEARCH-17349 | subject_age | 0          | expect_column_values_to_be_between | warning   |

The first column identifies the SEARCH id of the problematic metadata record, while the
second indicates which column of the metadata was of concern and the third reports
the value for that record in that column.  `fail_check`, the fourth column, 
specifies which of the validation checks this value triggered, and the fifth column, `fail_type`,
indicates whether the issue identified is a failure or a warning (as defined above). Details on the fail check definitions, if needed, can be found in the json files 
in the `great_expectations/expectations` subfolder.

## Installation

This installation is based on [conda](https://docs.conda.io/en/latest/) and git, 
and these instructions assume both these tools have already been installed. They have been tested only for Mac OS systems.

1. Begin by creating a new conda virtual environment, installing Great Expectations, and ensuring that it is working

```
conda create --name inspectseq_metadata_validator pyyaml pandas
conda activate inspectseq_metadata_validator
conda install -c conda-forge great-expectations
great_expectations --version
```

2. Clone this repository into a new folder named `inspectseq_metadata_validator` and install its code

```
git clone https://github.com/AmandaBirmingham/inspectseq_metadata_validator.git
cd inspectseq_metadata_validator
pip install -e .
```

3. Set the absolute file path to the yaml file of allowable locations
   1. Determine the absolute path, on your system to the newly-installed `inspectseq_metadata_validator/great_expectations/plugins/expectations/expect_column_values_to_parse_into_expected_locations_config.yaml` file
   2. Open `inspectseq_metadata_validator/great_expectations/expectations/inspectseq_metadata_warning_draft5.json`
   3. Locate the key `"allowed_locations_abs_fp"` and replace its placeholder value (`"/absolute/path/to/local/inspectseq_metadata_validator/great_expectations/plugins/expectations/expect_column_values_to_parse_into_expected_locations_config.yaml"`) with the absolute path determined in step 3.i

4. Initialize the Great Expectations installation
   1. Change directory to the `inspectseq_metadata_validator` folder
   2. ONLY **AFTER** resetting the absolute locations file path as described in step 3,
      1. Run `great_expectations init`

5. Add the datasource definition to the main configuration file created by the `init`
   1. Open the `inspectseq_metadata_validator/great_expectations.yml` file
   2. Replace the existing `datasources: {}` line with the below and save

```
datasources:
  inspectseq_metadata:
    module_name: great_expectations.datasource
    execution_engine:
      module_name: great_expectations.execution_engine
      class_name: PandasExecutionEngine
    data_connectors:
      default_runtime_data_connector_name:
        class_name: RuntimeDataConnector
        module_name: great_expectations.datasource.data_connector
        batch_spec_passthrough:
          reader_options:
            na_values: ''
            keep_default_na: False
        batch_identifiers:
          - default_identifier_name
    class_name: Datasource
```


## Usage

1. Download the newest metadata file to the local machine
   1. The metadata must be a `.csv` file beginning with the prefix `all_samples_search_ids_`
   2. If it is desirable to run differential reports between this and a previous metadata version, ensure that the new metadata file is placed in the same directory as the previous reports!
2. At the command line, activate the validator's conda environment:

```
conda activate inspectseq_metadata_validator
```

3. Capture the locations used in the new metadata file into a temporary yaml file
   1. In the below command, replace `/path/to/all_samples_search_ids_<latest>.csv` with the path to the metadata file downloaded in step 1
```
cd inspectseq_metadata_validator  # if not already there
```
```
capture_metadata_locations /path/to/all_samples_search_ids_<latest>.csv temp_locations.yaml
```

4. Compare the current locations with the last known locations
   1. The goal here is to look, visually, for any "fishy" ones, such as misspellings, locations missing the continent designation, and so forth
   2. Note that this step depends on `opendiff`, which is installed as part of XCode.  Any other diff tool would do, but might require different syntax 
   3. If using `opendiff`, MAKE SURE the `FileMerge` program is NOT currently open or the below commands won't work
   4. Be aware that `opendiff` may throw a bunch of errors to the terminal saying `Couldn't load language spec for '<DVTSourceCodeLanguage:0x7fca03882e10:'Xcode.SourceCodeLanguage.YAML'>`.  It is ok to ignore these :) Just ctrl-C in the terminal to end `opendiff` when done looking at the diffs

```
cd inspectseq_metadata_validator  # if not already there
```
```
opendiff great_expectations/plugins/expectations/expect_column_values_to_parse_into_expected_locations_config.yaml temp_locations.yaml
```

5. Act on the `opendiff` results
   1. If no differences are found, move to the next step
   2. If problems are found, correct the metadata file and begin the entire usage again
   3. If no problems are found but there ARE differences, copy the current temporary locations into the yaml file used for metadata validation.  These constitute the new set of "allowable" locations 

```
cd inspectseq_metadata_validator  # if not already there 
```
```
cp temp_locations.yaml great_expectations/plugins/expectations/expect_column_values_to_parse_into_expected_locations_config.yaml 
```

6. Generate the metadata validation reports, which will be placed in the same directory as the input metadata file 
   1. As noted above, to run differential reports between this and a previous metadata version, ensure that the previous reports are also in the directory with the new input metadata file

```
cd inspectseq_metadata_validator  # if not already there 
```
```
generate_metadata_reports /path/to/all_samples_search_ids_<latest>.csv
```
