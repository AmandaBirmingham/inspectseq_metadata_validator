import pandas
import yaml
from sys import argv


def collect_unique_locations(test_metadata):
    value_set = list(test_metadata.sample_collection_location.unique())

    known_values = {}
    for i in value_set:
        print(i)
        if not type(i) == str:
            continue

        pieces = i.split("/")
        if len(pieces) < 1:
            raise ValueError("No location info")
        elif len(pieces) > 4:
            raise ValueError(f"Location is longer than expected: {i}")

        curr_dict = known_values
        piece_0 = piece_1 = piece_2 = None
        for piece_index in range(len(pieces)):
            curr_piece = pieces[piece_index]
            if curr_piece:
                if piece_index == 0:
                    piece_0 = curr_piece.strip()
                    if piece_0 not in curr_dict:
                        known_values[piece_0] = {}
                    curr_dict = known_values[piece_0]
                elif piece_index == 1:
                    piece_1 = curr_piece.strip()
                    if piece_1 not in curr_dict:
                        known_values[piece_0][piece_1] = {}
                    curr_dict = known_values[piece_0][piece_1]
                elif piece_index == 2:
                    piece_2 = curr_piece.strip()
                    if piece_2 not in curr_dict:
                        known_values[piece_0][piece_1][piece_2] = {}
                    curr_dict = known_values[piece_0][piece_1][piece_2]
                elif piece_index == 3:
                    piece_3 = curr_piece.strip()
                    if curr_piece not in curr_dict:
                        known_values[piece_0][piece_1][piece_2][piece_3] = {}
                else:
                    raise ValueError("piece_index > 3")

    return known_values


def generate_unique_locations_yaml(input_fp, output_fp):
    test_metadata = pandas.read_csv(input_fp)

    known_values = collect_unique_locations(test_metadata)

    with open(output_fp, 'w') as yamlfile:
        yaml.dump(known_values, yamlfile)
        print("Locations yaml write successful")


def main():
    input_fp = argv[1]
    output_fp = argv[2]

    generate_unique_locations_yaml(input_fp, output_fp)


if __name__ == '__main__':
    # example usage:
    # capture_metadata_locations \
    #   /Users/abirmingham/Desktop/covid_temp/all_samples_search_ids_20220419.csv \
    #   /Users/abirmingham/Desktop/covid_temp/metadata/temp_locations.yaml

    # result, after verification, should be used to replace:
    #   inspectseq_metadata_validator/great_expectations/plugins/expectations/expect_column_values_to_parse_into_expected_locations_config.yaml

    main()
