import argparse

import create_wrap_update

if __name__ == "__main__":
    # define the message that will be displayed when the user runs the script with the -h flag
    msg = "A command line update script for wrapdb projects.\n"
    msg += "This script can clone a repo, update the wrap file, and push the changes to a fork of the wrapdb repo.\n"

    # create an ArgumentParser object to parse command line arguments
    parser = argparse.ArgumentParser(
        description=msg
    )

    # add the url argument
    parser.add_argument(
        "--url",
        "-u",
        help="The url of the project to update",
        required=True,
        dest='source_url',
        type=str,
    )

    # add the tag argument
    parser.add_argument(
        "--tag",
        "-t",
        help="The tag of the project to update",
        required=True,
        dest='tag',
        type=str,
    )

    # add the provides argument
    parser.add_argument(
        "--provides",
        "-p",
        help="The provides of the project to update (separated by commas)",
        required=True,
        dest='provides',
        type=str,
    )

    # add the push url argument
    parser.add_argument(
        "--push-url",
        help="The url of the fork of the wrapdb repo to push to",
        required=True,
        dest='push_url',
        type=str,
    )

    # add the name override argument
    parser.add_argument(
        "--name",
        "-n",
        help="Override the name of the project default is the repo name",
        required=False,
        default='',
        dest='name_override',
        type=str,
    )

    args = vars(parser.parse_args())

    # split the provides argument into a list
    if ',' in args['provides']:
        project_provides = args['provides'].split(',')
    else:
        project_provides = [args['provides']]

    # create the WrapProject object
    project = create_wrap_update.WrapProject(
        args['source_url'],
        args['tag'],
        project_provides,
        args['push_url'],
        args['name_override'],
    )

    # create the wrap file
    project.create_wrap_file()

