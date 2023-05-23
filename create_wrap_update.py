import json
import os.path
from hashlib import sha256
from typing import Dict, List

import jinja2
import git
import semver
import wget as wget


class WrapProject(Dict):
    def __init__(
        self,
        project_url: str,
        project_tag: str,
        project_provides: List[str],
        push_url: str,
        project_name: str = '',
        allow_cloned_repos: bool = True,
    ):
        super().__init__()

        if project_url.endswith('.git'):
            project_url = project_url[:-4]

        self["url"] = project_url

        # get the source repo, the project name and check if the tag exists
        if project_name == '':
            project_name = os.path.basename(project_url)

        self["name"] = project_name

        try:
            if allow_cloned_repos and os.path.isdir(project_name):
                repo = git.Repo(project_name)
                repo.git.fetch('--all')
            else:
                repo = git.Repo.clone_from(project_url, project_name)
        except git.exc.GitCommandError:
            raise Exception("Error cloning source repo")

        try:
            repo.git.checkout(project_tag)
            self["tag"] = project_tag
        except git.exc.GitCommandError:
            raise Exception("Error checking out tag. It might not exist")

        try:
            if project_tag.startswith('v') or project_tag.startswith('V'):
                semantic_version = semver.VersionInfo.parse(project_tag[1:])
            else:
                semantic_version = semver.VersionInfo.parse(project_tag)

            self["version"] = str(semantic_version.finalize_version())
        except ValueError:
            raise Exception("Error parsing tag as semantic version")

        # check if provides are given and valid
        if len(project_provides) == 0:
            raise Exception("No provides specified")

        # check if the push url is valid
        try:
            if allow_cloned_repos and os.path.isdir('wrapdb'):
                push_repo = git.Repo('wrapdb')
                push_repo.git.fetch('--all')
            else:
                push_repo = git.Repo.clone_from(push_url, 'wrapdb')
        except git.exc.GitCommandError:
            raise Exception("Error cloning push repo")

        # add upstream project as remote
        try:
            if 'upstream' not in push_repo.remotes:
                git.Remote.add(repo=push_repo, name='upstream', url='https://github.com/mesonbuild/wrapdb')

            push_repo.git.fetch('upstream')
            push_repo.git.checkout('-B', 'upstream/master')
        except git.exc.GitCommandError:
            raise Exception("Error adding upstream remote")

        # load the releases json file from the wrapdb repo
        try:
            releases_file_path = os.path.join('wrapdb', 'releases.json')

            releases_file = open(releases_file_path, 'r')
            releases_data = releases_file.read()
            releases_file.close()

            self.json_releases = json.loads(releases_data)
        except FileNotFoundError:
            raise Exception("Error loading releases.json")

        # create a new branch from upstream/master
        try:
            self.push_branch = 'update-' + project_name
            self.push_branch += '-' + self["version"]
            self.push_branch += '-' + str(self.get_next_build_number())
            push_repo.git.checkout('-B', self.push_branch)

            push_repo.git.rebase('upstream/master')
        except git.exc.GitCommandError:
            raise Exception("Error while branching or updating the branch")

        # download the release archive and get its hash
        self["archive_url"] = project_url + '/archive/refs/tags/' + project_tag + '.tar.gz'
        self["archive_filename"] = project_name + '-' + self["version"] + '.tar.gz'
        try:
            # delete the file if it already exists to make sure the correct one is downloaded
            if os.path.isfile(self["archive_filename"]):
                os.remove(self["archive_filename"])

            wget.download(self["archive_url"], out=self["archive_filename"], bar=None)
            sha256sum = sha256()
            with open(self["archive_filename"], 'rb') as fd:
                data_chunk = fd.read(1024)
                while data_chunk:
                    sha256sum.update(data_chunk)
                    data_chunk = fd.read(1024)
            self["archive_sha256"] = sha256sum.hexdigest()
        except Exception:
            raise Exception("Error downloading release archive")

        self["provides"] = project_provides
        self["push_url"] = push_url

    def create_wrap_file(self):
        # load the template
        template_file = open("wrapfile.template", "r")
        template = jinja2.Template(template_file.read())
        template_file.close()

        # fill the template and write it to a file
        output_file_name = self["name"] + ".wrap"
        wrap_file = open(output_file_name, "w")
        wrap_file.write(template.render(self))
        wrap_file.close()

    def get_next_build_number(self) -> int:
        try:
            release = self.json_releases[self["name"]]
        except KeyError:
            raise Exception("Key not found in releases.json make sure this library is already in the wrapdb repo")

        try:
            versions = release["versions"]

            for version in versions:
                semantic_version = semver.VersionInfo.parse(version)
                if semantic_version.finalize_version() == self["version"]:
                    return int(semantic_version.bump_prerelease().prerelease)

        except ValueError:
            raise Exception("Error parsing tag as semantic version")

        return 1

    def update_wrapdb_repo(self):
        output_file_name = self["name"] + ".wrap"

        if not os.path.isfile(output_file_name):
            self.create_wrap_file()

        # move the wrap file into wrapdb/subprojects
        output_file_path = os.path.join('wrapdb', 'subprojects', output_file_name)
        os.rename(output_file_name, output_file_path)

        # load the releases json file from the wrapdb repo
        releases_file_path = os.path.join('wrapdb', 'releases.json')

        build_number = self.get_next_build_number()
        new_version = self["version"] + '-' + str(build_number)
        self.json_releases[self["name"]]["versions"].insert(0, new_version)

        # write the new releases json file
        releases_file = open(releases_file_path, 'w')
        releases_file.write(json.dumps(self.json_releases, indent=2))
        releases_file.write('\n')
        releases_file.close()

    def commit_and_push_wrapdb(self):
        push_repo = git.Repo('wrapdb')

        wrap_file_path = os.path.join('subprojects', self["name"] + '.wrap')
        push_repo.git.add(wrap_file_path)
        push_repo.git.add('releases.json')

        push_repo.git.commit('-m', 'Update ' + self["name"] + ' to ' + self["version"])
        push_repo.git.push('origin', self.push_branch)
