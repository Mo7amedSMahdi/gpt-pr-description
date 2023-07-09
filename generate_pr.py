#!/usr/bin/env python3
import sys
import requests
import argparse
import json
import openai
import os

SAMPLE_PROMPT = """
Write a pull request description focusing on the motivation behind the change and why it improves the project.
Go straight to the point.

The title of the pull request is "Enable valgrind on CI" and the following changes took place: 

Changes in file diff --git a/src/pages/login/index.jsx b/src/pages/login/index.jsx
index 4762570..3120b52 100644
--- a/src/pages/login/index.jsx
+++ b/src/pages/login/index.jsx
@@ -4,17 +4,15 @@ import Card from '@mui/material/Card';
 import CardContent from '@mui/material/CardContent';
 import Typography from '@mui/material/Typography';
 import TextField from '@mui/material/TextField';
-import { Button, InputAdornment } from '@mui/material';
+import { InputAdornment } from '@mui/material';
 import { LoadingButton } from '@mui/lab';
 import VisibilityIcon from '@mui/icons-material/Visibility';
 import VisibilityOffIcon from '@mui/icons-material/VisibilityOff';
 import loginImg from '../../assets/images/login.png';
 import Background from '../../assets/images/backgroundLogin.png';
-// import Auth from '../auth/models/authModel';
 import authUser from '../auth/models/authModel';
 import { toast } from 'react-toastify';
 import { useNavigate } from 'react-router-dom';
-import { useAppContext } from '../../context/AppContext';
 
 export default function Login() {
   const [showPassword, setShowPassword] = React.useState(false);
@@ -24,7 +22,6 @@ export default function Login() {
   const navigate = useNavigate();
 
   const handleLogin = async () => {
-    // const authInstance = new Auth();
     setLoading(true);
     await authUser
       .signIn(email, password)
diff --git a/theme/index.js b/theme/index.js
index ad95e1c..0be6be7 100644
--- a/theme/index.js
+++ b/theme/index.js
@@ -180,6 +180,49 @@ const theme = createTheme({
               marginLeft: '5px',
             },
           },
+          '&.text-area': {
+            '& .MuiInputBase-root': {
+              paddingInline: '1.5rem',
+              fontWeight: 400,
+              fontSize: '1.25rem',
+              color: '#969696',
+              '& label': {
+                marginLeft: '1.5rem',
+                color: colors.gray,
+              },
+              '& input': {
+                zIndex: 1,
+              },
+              '& textarea': {
+                zIndex: 1,
+              },
+              '& fieldset': {
+                borderRadius: '20px !important',
+                borderColor: 'none',
+                border: 'none ',
+                backgroundColor: colors.whiteGray,
+                '& legend': {
+                  marginLeft: '1.5rem',
+                },
+              },
+              '&:hover fieldset': {
+                borderColor: colors.blue,
+              },
+              '&.Mui-focused fieldset': {
+                borderColor: colors.blue,
+                borderWidth: '1px',
+                borderStyle: 'solid',
+              },
+            },
+            '& .MuiSelect-select': {
+              zIndex: 1,
+            },
+            '& .MuiTypography-root': {
+              zIndex: 1,
+              color: colors.gray,
+              marginLeft: '5px',
+            },
+          },
           '& label.Mui-focused': {
             color: colors.blue,
           },
@@ -222,6 +265,16 @@ const theme = createTheme({
         },
       },
     },
+    MuiDialogActions: {
+      styleOverrides: {
+        root: {
+          display: 'flex',
+          justifyContent: 'space-between',
+          alignItems: 'center',
+          paddingInline: '0px',
+        },
+      },
+    },
   },
 });
"""

GOOD_SAMPLE_RESPONSE = """
# Pull Request Description

## :rocket: feat: Remove unused dependencies and commented code in login page

- Removed unused `Button` component import from `@mui/material`.
- Removed commented code that imported `Auth` from `../auth/models/authModel`.
- Removed unused import of `useAppContext` from `../../context/AppContext`.

ℹ️ The changes were done to clean up the code and remove unnecessary dependencies and commented code that were not being used.

## :wrench: Fix import and render issues in main.jsx

- Fixed import issues in `main.jsx` where the `App` component was not correctly imported.
- Fixed rendering issues in `main.jsx` by using `ReactDOM.createRoot` instead of `ReactDOM.render`.
- Updated code to use `LazyApp` instead of directly importing the `App` component.
- Added `ReactQueryDevtools` to `main.jsx`.
"""


def main():
    parser = argparse.ArgumentParser(
        description="Use ChatGPT to generate a description for a pull request."
    )
    parser.add_argument(
        "--github-api-url", type=str, required=True, help="The GitHub API URL"
    )
    parser.add_argument(
        "--github-repository", type=str, required=True, help="The GitHub repository"
    )
    parser.add_argument(
        "--pull-request-id",
        type=int,
        required=True,
        help="The pull request ID",
    )
    parser.add_argument(
        "--github-token",
        type=str,
        required=True,
        help="The GitHub token",
    )
    parser.add_argument(
        "--openai-api-key",
        type=str,
        required=True,
        help="The OpenAI API key",
    )
    parser.add_argument(
        "--allowed-users",
        type=str,
        required=False,
        help="A comma-separated list of GitHub usernames that are allowed to trigger the action, empty or missing means all users are allowed",
    )
    args = parser.parse_args()

    github_api_url = args.github_api_url
    repo = args.github_repository
    github_token = args.github_token
    pull_request_id = args.pull_request_id
    openai_api_key = args.openai_api_key
    allowed_users = os.environ.get("INPUT_ALLOWED_USERS", "")
    if allowed_users:
        allowed_users = allowed_users.split(",")
    open_ai_model = os.environ.get("INPUT_OPENAI_MODEL", "gpt-3.5-turbo")
    max_prompt_tokens = int(os.environ.get("INPUT_MAX_TOKENS", "1000"))
    model_temperature = float(os.environ.get("INPUT_TEMPERATURE", "0.6"))
    model_sample_prompt = os.environ.get("INPUT_MODEL_SAMPLE_PROMPT", SAMPLE_PROMPT)
    model_sample_response = os.environ.get(
        "INPUT_MODEL_SAMPLE_RESPONSE", GOOD_SAMPLE_RESPONSE
    )
    authorization_header = {
        "Accept": "application/vnd.github.v3+json",
        "Authorization": "token %s" % github_token,
    }

    pull_request_url = f"{github_api_url}/repos/{repo}/pulls/{pull_request_id}"
    pull_request_result = requests.get(
        pull_request_url,
        headers=authorization_header,
    )
    if pull_request_result.status_code != requests.codes.ok:
        print(
            "Request to get pull request data failed: "
            + str(pull_request_result.status_code)
        )
        return 1
    pull_request_data = json.loads(pull_request_result.text)

    # if pull_request_data["body"]:
    #     print("Pull request already has a description, skipping")
    #     return 0

    if allowed_users:
        pr_author = pull_request_data["user"]["login"]
        if pr_author not in allowed_users:
            print(
                f"Pull request author {pr_author} is not allowed to trigger this action"
            )
            return 0

    pull_request_title = pull_request_data["title"]

    pull_request_files = []
    # Request a maximum of 10 pages (300 files)
    for page_num in range(1, 11):
        pull_files_url = f"{pull_request_url}/files?page={page_num}&per_page=30"
        pull_files_result = requests.get(
            pull_files_url,
            headers=authorization_header,
        )

        if pull_files_result.status_code != requests.codes.ok:
            print(
                "Request to get list of files failed with error code: "
                + str(pull_files_result.status_code)
            )
            return 1

        pull_files_chunk = json.loads(pull_files_result.text)

        if len(pull_files_chunk) == 0:
            break

        pull_request_files.extend(pull_files_chunk)

        completion_prompt = f"""
Write a pull request description focusing on the motivation behind the change and why it improves the project.
Go straight to the point.

The title of the pull request is "{pull_request_title}" and the following changes took place: \n
"""
    for pull_request_file in pull_request_files:
        # Not all PR file metadata entries may contain a patch section
        # For example, entries related to removed binary files may not contain it
        if "patch" not in pull_request_file:
            continue

        filename = pull_request_file["filename"]
        patch = pull_request_file["patch"]
        completion_prompt += f"Changes in file {filename}: {patch}\n"

    max_allowed_tokens = 2048  # 4096 is the maximum allowed by OpenAI for GPT-3.5
    characters_per_token = 4  # The average number of characters per token
    max_allowed_characters = max_allowed_tokens * characters_per_token
    if len(completion_prompt) > max_allowed_characters:
        completion_prompt = completion_prompt[:max_allowed_characters]

    openai.api_key = openai_api_key
    openai_response = openai.ChatCompletion.create(
        model=open_ai_model,
        messages=[
            {
                "role": "system",
                "content": "You are a helpful assistant who writes pull request descriptions",
            },
            {"role": "user", "content": model_sample_prompt},
            {"role": "assistant", "content": model_sample_response},
            {"role": "user", "content": completion_prompt},
        ],
        temperature=model_temperature,
        max_tokens=max_prompt_tokens,
    )

    generated_pr_description = openai_response.choices[0].message.content
    redundant_prefix = "This pull request "
    if generated_pr_description.startswith(redundant_prefix):
        generated_pr_description = generated_pr_description[len(redundant_prefix) :]
        generated_pr_description = (
            generated_pr_description[0].upper() + generated_pr_description[1:]
        )
    print(f"Generated pull request description: '{generated_pr_description}'")
    issues_url = "%s/repos/%s/issues/%s" % (
        github_api_url,
        repo,
        pull_request_id,
    )
    update_pr_description_result = requests.patch(
        issues_url,
        headers=authorization_header,
        json={"body": generated_pr_description},
    )

    if update_pr_description_result.status_code != requests.codes.ok:
        print(
            "Request to update pull request description failed: "
            + str(update_pr_description_result.status_code)
        )
        print("Response: " + update_pr_description_result.text)
        return 1


if __name__ == "__main__":
    sys.exit(main())