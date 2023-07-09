#!/usr/bin/env python3

import sys
import requests
import json
import os
import argparse
import openai


SAMPLE_PROMPT = """
Write a pull request description focusing on the motivation behind the change and why it improves the project.
Go straight to the point.

The title of the pull request is "Enable valgrind on CI" and the following changes took place: 

Changes in file .github/workflows/build-ut-coverage.yml: @@ -24,6 +24,7 @@ jobs:
         run: |
           sudo apt-get update
           sudo apt-get install -y lcov
+          sudo apt-get install -y valgrind
           sudo apt-get install -y ${{ matrix.compiler.cc }}
           sudo apt-get install -y ${{ matrix.compiler.cxx }}
       - name: Checkout repository
@@ -48,3 +49,7 @@ jobs:
         with:
           files: coverage.info
           fail_ci_if_error: true
+      - name: Run valgrind
+        run: |
+          valgrind --tool=memcheck --leak-check=full --leak-resolution=med \
+            --track-origins=yes --vgdb=no --error-exitcode=1 ${build_dir}/test/command_parser_test
Changes in file test/CommandParserTest.cpp: @@ -566,7 +566,7 @@ TEST(CommandParserTest, ParsedCommandImpl_WhenArgumentIsSupportedNumericTypeWill
     unsigned long long expectedUnsignedLongLong { std::numeric_limits<unsigned long long>::max() };
     float expectedFloat { -164223.123f }; // std::to_string does not play well with floating point min()
     double expectedDouble { std::numeric_limits<double>::max() };
-    long double expectedLongDouble { std::numeric_limits<long double>::max() };
+    long double expectedLongDouble { 123455678912349.1245678912349L };
 
     auto command = UnparsedCommand::create(expectedCommand, "dummyDescription"s)
                        .withArgs<int, long, unsigned long, long long, unsigned long long, float, double, long double>();
"""

RESPONSE_SAMPLE = """
Currently, our CI build does not include Valgrind as part of the build and test process. Valgrind is a powerful tool for detecting memory errors, and its use is essential for maintaining the integrity of our project.
This pull request adds Valgrind to the CI build, so that any memory errors will be detected and reported immediately. This will help to prevent undetected memory errors from making it into the production build.

Overall, this change will improve the quality of the project by helping us detect and prevent memory errors.
"""

def main():
    parser = argparse.ArgumentParser(description='Generate a pull request description using GPT-3')
    parser.add_argument("--github-api-url",type=str,help="Github API URL",default="https://api.github.com",required=True)
    parser.add_argument("--github-token",type=str,help="Github token",required=True)
    parser.add_argument("--github-repo",type=str,help="Github repo",required=True)
    parser.add_argument("--pull-request-id",type=int,help="Github PR id",required=True)
    parser.add_argument("--openai-api-key",type=str,help="OpenAI API key",required=True)
    parser.add_argument("--allowed-users",type=str,help="A comma-separated list of GitHub usernames that are allowed to trigger the action, empty or missing means all users are allowed",required=False)
    
    args = parser.parse_args()

    github_api_url = args.github_api_url
    github_token = args.github_token
    github_repo = args.github_repo
    pull_request_id = args.pull_request_id
    openai_api_key = args.openai_api_key
    allowed_users = os.environ.get("INPUT_ALLOWED_USERS", "")
    if allowed_users:
        allowed_users = allowed_users.split(",")
    openai_model = os.environ.get("INPUT_OPENAI_MODEL", "gpt-3.5-turbo")
    max_prompt_token = int(os.environ.get("INPUT_MAX_PROMPT_TOKEN", "1048"))
    openai_temperature = float(os.environ.get("INPUT_OPENAI_TEMPERATURE", "0.7"))
    model_sample_prompt = os.environ.get("INPUT_MODEL_SAMPLE_PROMPT", SAMPLE_PROMPT)
    model_sample_response = os.environ.get(
        "INPUT_MODEL_SAMPLE_RESPONSE", RESPONSE_SAMPLE
    )
    auth_header = {"Accept":"application/vnd.github.v3+json","Authorization":f"token %s" % github_token}

    pull_request_url = f"{github_api_url}/repos/{github_repo}/pulls/{pull_request_id}"
    pull_request_result = requests.get(pull_request_url,headers=auth_header)

    if pull_request_result.status_code != requests.codes.ok:
        print(f"Failed to get pull request {pull_request_id} from {github_repo}" + str(pull_request_result.status_code))
        return 0
    pull_request_data = json.loads(pull_request_result.text)

    if pull_request_data['body']:
        print("Pull request already has a description")
        return 0
    
    if allowed_users:
        pull_request_author = pull_request_data['user']['login']
        if pull_request_author not in allowed_users:
            print(f"Pull request author {pull_request_author} is not allowed to trigger the action")
            return 0
        
    pull_request_title = pull_request_data['title']
    # Request a maximum of 10 pages (300 files)
    for page_num in range (1,11):
        pull_request_files_url = f"{github_api_url}/files?page={page_num}&per_page=30"
        pull_request_files_result = requests.get(pull_request_files_url,headers=auth_header)

        if pull_request_files_result.status_code != requests.codes.ok:
            print(f"Failed to get pull request {pull_request_id} files from {github_repo}" + str(pull_request_files_result.status_code))
            return 0
        
        pull_request_files_data = json.loads(pull_request_files_result.text)

        if len(pull_request_files_data) == 0:
            break
        ai_prompt = f"""
Write a pull request description focusing on the motivation behind the change and why it improves the project.
Go straight to the point.

The title of the pull request is "{pull_request_title}" and the following changes took place: \n
"""
        for file in pull_request_files_data:
            # Not all PR file metadata entries may contain a patch section
            # For example, entries related to removed binary files may not contain it
            if 'patch' not in file:
                continue
            file_name = file['filename']
            file_patch = file['patch']
            ai_prompt += f"Changes in file {file_name}: {file_patch}\n"

        
        max_allowed_tokens = 2048
        chars_per_token = 4
        max_allowed_chars = max_prompt_token * chars_per_token
        if len(ai_prompt) > max_allowed_chars:
            ai_prompt = ai_prompt[:max_allowed_chars]

        openai.api_key = openai_api_key
        openai_response = openai.Completion.create(
            model=openai_model,
            messages=[{
                "role":"system",
                "content":"You are a helpful assistant who writes pull request descriptions",
            },
            {"role": "user", "content": model_sample_prompt},
            {"role": "assistant", "content": model_sample_response},
            {"role": "user", "content": ai_prompt},
            ],
            temperature=openai_temperature,
            max_tokens=max_prompt_token,
        )
        generated_pr_description = openai_response.choices[0].message.content
        redundant_prefix = "This pull request description was generated by an AI assistant."
        if generated_pr_description.startswith(redundant_prefix):
            generated_pr_description = generated_pr_description[len(redundant_prefix):]
        generated_pr_description = generated_pr_description[0].upper() + generated_pr_description[1:]
        print(f"Generated PR description:\n{generated_pr_description}")
        issues_url = "%s/repos/%s/issues/%s" % (github_api_url,github_repo,pull_request_id)
        update_pr_description_result = requests.patch(issues_url,headers=auth_header,json={"body":generated_pr_description})

        if update_pr_description_result.status_code != requests.codes.ok:
            print(f"Failed to update pull request {pull_request_id} description from {github_repo}" + str(update_pr_description_result.status_code))
            print("Response: " + update_pr_description_result.text)
            return 1
        
    if __name__ == "__main__":
        sys.exit(main())
        