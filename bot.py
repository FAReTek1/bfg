import json
import os
import pprint
import re
import base64

from furl import furl
from github import Github, Auth, ContentFile, Issue

# os.environ["BFG_PAT_GITHUB"]
auth = Auth.Token(open("PAT").read())
gh = Github(auth=auth)

REPO = gh.get_user().get_repo("inflate-gtp")

class GTP:
    @property
    def raw_data(self) -> str:
        raw = REPO.get_contents("gtp.json")
        assert isinstance(raw, ContentFile.ContentFile)
        assert raw.encoding == "base64"

        return base64.b64decode(raw.content).decode()

    @raw_data.setter
    def raw_data(self, value: str):
        REPO.update_file("gtp.json", "update gtp.raw_data", value, REPO.get_contents("gtp.json").sha)

    @property
    def data(self) -> dict[str, str]:
        return json.loads(self.raw_data)

    @data.setter
    def data(self, value: dict[str, str]):
        self.raw_data = json.dumps(value)

    def __setitem__(self, key: str, value: str):
        data = self.data
        data[key] = value
        self.data = data

gtp = GTP()

def main():
    for issue in REPO.get_issues(
            state="open",
            labels=["register"]
    ):
        body = issue.body

        if re.match(''
                    r"### Name\n\n"
                    r"[a-zA-Z0-9_-]+\n\n"
                    r"### URL\n\n"
                    r"https?://github\.com(/([a-zA-Z0-9._-]+)){2}/?", body):
            lines = body.splitlines()

            assert len(lines) == 7, f"Invalid body: {lines}"

            name = lines[2]
            url = furl(lines[6])

            register_package(name, url, issue)

        else:
            issue.create_comment("""\
This issue syntax is invalid.
- The name can only be made up of a-z, A-Z, underscores or dashes.
- The URL has to be a valid **GitHub** URL, to the root of the repository.\
""")
            issue.edit(state="closed",
                       state_reason="not_planned")

def register_package(name: str, url: furl, issue: Issue.Issue):
    message = ""
    def mlog(msg, end: str = '\n'):
        nonlocal message
        message += str(msg) + end

    mlog(f"- Registering `{name!r}` for `{url}`")

    data = gtp.data
    data_rev = {v: k for k, v in data.items()}

    url_str = parse_url(url)
    mlog(f"- Parsed furl as `{url_str}`")

    if existing_url := data.get(name):
        if existing_url == url_str:
            mlog("## This was already registered!")

            issue.create_comment(message)
            issue.edit(state="closed", state_reason="duplicate")
            return

        mlog(f"## Oh no, name already taken: `{existing_url}`")

        issue.create_comment(message)
        issue.edit(state="closed", state_reason="not_planned")
        return

    if existing_name := data_rev.get(url_str):
        mlog(f"## Repo already registered as `{existing_name}`")

        issue.create_comment(message)
        issue.edit(state="closed", state_reason="not_planned")
        return

    gtp[name] = url_str
    mlog("## Added!! See [gtp.json](https://github.com/FAReTek1/inflate-gtp/blob/main/gtp.json)!")

    issue.create_comment(message)
    issue.edit(state="closed")


def parse_url(url: furl) -> str:
    return "https://github.com/" + '/'.join(url.path.segments)


if __name__ == '__main__':
    main()