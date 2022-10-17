# inspectseq_metadata_validator

Tools to validate InspectSeq metadata files for use in C-VIEW.  These tools are
built on the [Great Expectations](https://greatexpectations.io/) software package.

## Installation

This installation is based on [conda](https://docs.conda.io/en/latest/) and has
been tested only for Mac OS systems.

Begin by creating a new conda virtual environment and installing Great Expectations:

Modify the `great_expectations.yml` file to replace the default, empty datasources 
declaration (`datasources = {}`) with the below:

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

Download the newest metadata file to the local machine.

At the command line, activate the validator's conda environment:

`conda activate inspectseq_metadata_validator`

Capture the locations used in the new metadata file into a temporary yaml file:

capture_locations_from_metadata_csv /Users/abirmingham/Desktop/covid_temp/metadata/all_samples_search_ids_20221006.csv /Users/abirmingham/Desktop/covid_temp/metadata/temp_locations.yaml

######################################################################################
# NB: MAKE SURE the FileMerge program is NOT currently open or the below won't work! #
######################################################################################

# compare the current locations with the last known locations and look for any "fishy" ones--
# such as misspellings, locations missing the continent designation, etc
opendiff ../great_expectations/plugins/expectations/expect_column_values_to_parse_into_expected_locations_config.yaml /Users/abirmingham/Desktop/covid_temp/metadata/temp_locations.yaml


# NB: opendiff will throw a bunch of errors to the terminal saying 
# "Couldn't load language spec for '<DVTSourceCodeLanguage:0x7fca03882e10:'Xcode.SourceCodeLanguage.YAML'>' 
# It is ok to ignore these.
# Just ctrl-C in the terminal to end opendiff when done looking at the diffs

# if no problems are found but there ARE differences, copy the current locations to the yaml file used for metadata validation 
cp /Users/abirmingham/Desktop/covid_temp/metadata/temp_locations.yaml ../great_expectations/plugins/expectations/expect_column_values_to_parse_into_expected_locations_config.yaml 

# run metadata validation
cd /Users/abirmingham/Work/Repositories/cview-utils/src
generate_metadata_validation_report /Users/abirmingham/Desktop/covid_temp/metadata/all_samples_search_ids_20221006.csv
