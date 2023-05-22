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
    ):
        super().__init__()

        if project_url.endswith('.git'):
            project_url = project_url[:-4]

        # get the source repo, the project name and check if the tag exists
        if project_name == '':
            project_name = os.path.basename(project_url)

        try:
            repo = git.Repo.clone_from(project_url, project_name)
        except git.exc.GitCommandError:
            raise Exception("Error cloning source repo")

        try:
            repo.git.checkout(project_tag)
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
            push_repo = git.Repo.clone_from(push_url, 'wrapdb')
        except git.exc.GitCommandError:
            raise Exception("Error cloning push repo")

        # add the upstream project as source and create a new branch from it
        try:
            git.Remote.add(repo=push_repo, name='upstream', url='https://github.com/mesonbuild/wrapdb')
            push_repo.git.fetch('upstream')
            push_repo.git.checkout('-b', 'upstream/master')

            self.push_branch = 'update-' + project_name + '-' + self["version"]
            push_repo.git.checkout('-b', self.push_branch)

            push_repo.git.rebase('upstream/master')
        except git.exc.GitCommandError:
            raise Exception("Error updating push url from upstream and branching")

        # download the release archive and get its hash
        self["archive_url"] = project_url + '/archive/refs/tags/' + project_tag + '.tar.gz'
        self["archive_filename"] = project_name + '_' + self["version"] + '.tar.gz'
        try:
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

        self["name"] = project_name
        self["url"] = project_url
        self["tag"] = project_tag
        self["provides"] = project_provides
        self["push_url"] = push_url

    def create_wrap_file(self):
        template_file = open("wrapfile.template", "r")
        template = jinja2.Template(template_file.read())
        template_file.close()

        output_file_name = self["name"] + ".wrap"
        wrap_file = open(output_file_name, "w")
        wrap_file.write(template.render(self))
        wrap_file.close()

