"""
Script to check that a site that went through a migration from
Github Pages to being versioned (PyData Sphinx Theme version switcher
+ CloudFront + S3) has its links working as expected.
"""
import argparse
import sys

import requests

EPILOG = """
Examples:
  # Test standard site with specific version
  %(prog)s test --base-url https://hvplot-test.holoviz.org --version 0.11.3

  # Run tests with verbose output
  %(prog)s test --base-url https://example.com --version 1.0.0 --verbose

  # Test GitHub Pages only with default URL
  %(prog)s github-pages
"""

DEFAULT_GITHUB_PAGES_URL = "https://holoviz.org/"


class SiteValidator:
    def __init__(self, base_url: str, version: str | None = None, verbose: bool = False):
        self.base_url = base_url.rstrip('/')
        self.version = version
        self.verbose = verbose
        self.failed_tests = []
        self.passed_tests = 0

    def log(self, message: str):
        """Print message if verbose mode is enabled."""
        if self.verbose:
            print(message)

    def check_redirect(self, path: str, expected_status: int, expected_location: str | None = None) -> bool:
        """Check if a path redirects as expected."""
        resp = requests.head(self.base_url + path, allow_redirects=False, timeout=10)

        # Check status code
        if resp.status_code != expected_status:
            self.failed_tests.append({
                'path': path,
                'error': f"Expected status {expected_status}, got {resp.status_code}",
                'response': resp
            })
            return False

        # Check location header if expected
        if expected_location and resp.headers.get('Location') != expected_location:
            self.failed_tests.append({
                'path': path,
                'error': f"Expected location '{expected_location}', got '{resp.headers.get('Location')}'",
                'response': resp
            })
            return False

        self.passed_tests += 1
        self.log(f"✓ {path} -> {expected_status} {expected_location or ''}")
        return True

    def check_response(self, path: str, expected_status: int, expected_content: str | None = None) -> bool:
        """Check if a path returns expected response."""
        resp = requests.get(self.base_url + path, allow_redirects=False, timeout=10)

        # Check status code
        if resp.status_code != expected_status:
            self.failed_tests.append({
                'path': path,
                'error': f"Expected status {expected_status}, got {resp.status_code}",
                'response': resp
            })
            return False

        # Check content if expected
        if expected_content and expected_content not in resp.text:
            self.failed_tests.append({
                'path': path,
                'error': f"Expected content '{expected_content}' not found",
                'response': resp
            })
            return False

        self.passed_tests += 1
        self.log(f"✓ {path} -> {expected_status}")
        return True

    def test_redirects_root_to_docs_latest(self):
        """Test redirects from root to /en/docs/latest/"""
        print("\n=== Testing root redirects to /en/docs/latest/ ===")
        paths = ["", "/", "/index.html", "/docs", "/docs/", "/en/docs", "/en/docs/"]

        for path in paths:
            self.check_redirect(path, 301, '/en/docs/latest/')

    def test_redirects_to_docs_latest(self):
        """Test redirects that add trailing slash."""
        print("\n=== Testing redirects that add trailing slash ===")
        paths = [
            "/en/docs/latest",
            "/en/docs/dev",
            f"/en/docs/{self.version}",
            "/en/docs/latest?key=value",
            "/en/docs/dev?key=value",
            f"/en/docs/{self.version}?key=value",
        ]

        for path in paths:
            if "?" in path:
                expected = path.replace("?", "/?")
            else:
                expected = path + "/"
            self.check_redirect(path, 301, expected)

    def test_old_to_new_redirects(self):
        """Test old URL pattern redirects to new pattern."""
        print("\n=== Testing old to new URL redirects ===")
        paths = ["/user_guide", "/user_guide?key=value"]

        for path in paths:
            if "?" in path:
                expected = "/en/docs/latest" + path.replace("?", "/?")
            else:
                expected = "/en/docs/latest" + path + "/"
            self.check_redirect(path, 301, expected)

    def test_pages_with_index(self):
        """Test pages that end with /index return 200."""
        print("\n=== Testing pages ending with /index ===")
        paths = ["/en/docs/latest/index", "/en/docs/latest/user_guide/index"]

        for path in paths:
            self.check_response(path, 200)

    def test_pages_with_slash(self):
        """Test pages that end with slash return 200."""
        print("\n=== Testing pages ending with slash ===")
        paths = ["/en/docs/latest/user_guide/"]

        for path in paths:
            self.check_response(path, 200)

    def test_file_urls_old_to_new(self):
        """Test file URLs old pattern redirects."""
        print("\n=== Testing pretty URLs old to new redirects ===")
        paths = ["/user_guide/Introduction.html", "/user_guide/Introduction.html?key=value"]

        for path in paths:
            expected = "/en/docs/latest" + path
            self.check_redirect(path, 301, expected)

    def test_pretty_urls_old_to_new(self):
        """Test pretty URLs old pattern redirects."""
        print("\n=== Testing pretty URLs old to new redirects ===")
        paths = ["/user_guide/Introduction", "/user_guide/Introduction?key=value"]

        for path in paths:
            if "?" in path:
                expected = "/en/docs/latest" + path.replace("?", ".html?")
            else:
                expected = "/en/docs/latest" + path + ".html"
            self.check_redirect(path, 301, expected)

    def test_pretty_urls(self):
        """Test pretty URLs return 200."""
        print("\n=== Testing pretty URLs ===")
        paths = [
            "/en/docs/latest/user_guide/Introduction",
            "/en/docs/latest/user_guide/Introduction?key=value"
        ]

        for path in paths:
            self.check_response(path, 200)

    def test_directories(self):
        """Test directory redirects."""
        print("\n=== Testing directory redirects ===")
        paths = [
            "/user_guide",
            "/en/docs/latest/user_guide",
            "/user_guide?key=value",
            "/en/docs/latest/user_guide?key=value",
        ]

        for path in paths:
            if "?" in path:
                expected = path.replace("?", "/?")
            else:
                expected = path + "/"
            if "/en/docs" not in expected:
                expected = "/en/docs/latest" + expected
            self.check_redirect(path, 301, expected)

    def test_github_pages_pretty_urls(self):
        """Test GitHub Pages specific pretty URLs."""
        print("\n=== Testing GitHub Pages pretty URLs ===")
        paths = ["/about/heps/hep0", "/about/heps/hep0?key=value"]  # codespell:ignore heps

        for path in paths:
            self.check_response(path, 200)

    def test_github_pages_directories(self):
        """Test GitHub Pages specific directory redirects."""
        print("\n=== Testing GitHub Pages directory redirects ===")
        paths = ["/about", "/about?key=value"]

        for path in paths:
            if "?" in path:
                expected = self.base_url + path.replace("?", "/?")
            else:
                expected = self.base_url + path + "/"
            self.check_redirect(path, 301, expected)

    def test_404_pages(self):
        """Test 404 pages."""
        print("\n=== Testing 404 pages ===")
        paths = ["/bad/", "/bad", "/bad.html", "/bad.xyz"]

        for path in paths:
            self.check_response(path, 404, "Sorry, we couldn't find the page you're looking for")

    def run_all_tests(self):
        """Run all standard tests."""
        self.test_redirects_root_to_docs_latest()
        self.test_redirects_to_docs_latest()
        self.test_old_to_new_redirects()
        self.test_file_urls_old_to_new()
        self.test_pages_with_index()
        self.test_pages_with_slash()
        self.test_pretty_urls_old_to_new()
        self.test_pretty_urls()
        self.test_directories()

    def run_github_pages_tests(self):
        """Run GitHub Pages specific tests."""
        self.test_github_pages_pretty_urls()
        self.test_github_pages_directories()
        self.test_404_pages()

    def print_summary(self):
        """Print test summary."""
        print(f"\n{'='*60}")
        print(f"TEST SUMMARY: {self.passed_tests} passed, {len(self.failed_tests)} failed")
        print(f"{'='*60}")

        if self.failed_tests:
            print("\nFAILED TESTS:")
            for test in self.failed_tests:
                print(f"\n❌ Path: {test['path']}")
                print(f"   Error: {test['error']}")
                if test['response']:
                    print(f"   Status: {test['response'].status_code}")
                    if 'Location' in test['response'].headers:
                        print(f"   Location: {test['response'].headers['Location']}")
                    if len(test['response'].text) < 200:
                        print(f"   Response: {test['response'].text[:200]}")
                    else:
                        print(f"   Response (truncated): {test['response'].text[:200]}...")


def main():
    parser = argparse.ArgumentParser(
        description="Validate site URLs and redirects",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=EPILOG,
    )

    subparsers = parser.add_subparsers(dest='command', help='Command to run')

    # Main test command
    test_parser = subparsers.add_parser('test', help='Run all validation tests')
    test_parser.add_argument('--base-url', required=True, help='Base URL of the site to test')
    test_parser.add_argument('--version', required=True, help='Specific version to test (e.g., 0.11.3)')
    test_parser.add_argument('--verbose', '-v', action='store_true', help='Enable verbose output')

    # GitHub Pages test command
    github_parser = subparsers.add_parser('github-pages', help='Run GitHub Pages specific tests')
    github_parser.add_argument('--verbose', '-v', action='store_true', help='Enable verbose output')

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    if args.command == 'test':
        validator = SiteValidator(args.base_url, args.version, args.verbose)
        print(f"Running validation tests for {args.base_url} (version: {args.version})")
        validator.run_all_tests()
        validator.print_summary()
        sys.exit(1 if validator.failed_tests else 0)

    elif args.command == 'github-pages':
        validator = SiteValidator(DEFAULT_GITHUB_PAGES_URL, verbose=args.verbose)
        print(f"Running GitHub Pages tests for {DEFAULT_GITHUB_PAGES_URL}")
        validator.run_github_pages_tests()
        validator.print_summary()
        sys.exit(1 if validator.failed_tests else 0)


if __name__ == "__main__":
    main()
