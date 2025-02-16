from github import Github
from github import Auth

from dotenv import load_dotenv
import os

load_dotenv()
access_token = os.getenv("ACCESS_TOKEN")

# using an access token
auth = Auth.Token(access_token)

# Public Web Github
g = Github(auth=auth)

for repo in g.get_user().get_repos():
    print(repo.name)
    # to see all the available attributes and methods
    # print(dir(repo))

g.close()
