#!/usr/bin/env python3
"""
Test script for MCP Router Service
Tests all endpoints and validates responses
"""
import requests
import json
import sys
import time
from typing import Dict, Any

# ANSI color codes
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
RESET = '\033[0m'

def print_success(msg: str):
    print(f"{GREEN}✓ {msg}{RESET}")

def print_error(msg: str):
    print(f"{RED}✗ {msg}{RESET}")

def print_info(msg: str):
    print(f"{BLUE}ℹ {msg}{RESET}")

def print_warning(msg: str):
    print(f"{YELLOW}⚠ {msg}{RESET}")

class MCPTester:
    def __init__(self, base_url: str = "http://localhost:7001", api_key: str = None):
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.headers = {"Content-Type": "application/json"}
        if api_key:
            self.headers["Authorization"] = f"Bearer {api_key}"

        self.passed = 0
        self.failed = 0

    def test_health(self) -> bool:
        """Test health check endpoint"""
        print("\n" + "="*60)
        print("Test 1: Health Check")
        print("="*60)

        try:
            response = requests.get(f"{self.base_url}/health", timeout=10)

            if response.status_code != 200:
                print_error(f"Status code: {response.status_code}")
                self.failed += 1
                return False

            data = response.json()
            print_info(f"Response: {json.dumps(data, indent=2)}")

            # Validate response structure
            required_fields = ["status", "model", "device", "model_loaded"]
            for field in required_fields:
                if field not in data:
                    print_error(f"Missing field: {field}")
                    self.failed += 1
                    return False

            if data["status"] != "healthy":
                print_error(f"Service is not healthy: {data['status']}")
                self.failed += 1
                return False

            if not data["model_loaded"]:
                print_error("Model is not loaded")
                self.failed += 1
                return False

            print_success(f"Service is healthy on {data['device']}")
            self.passed += 1
            return True

        except requests.exceptions.RequestException as e:
            print_error(f"Request failed: {e}")
            self.failed += 1
            return False

    def test_info(self) -> bool:
        """Test server info endpoint"""
        print("\n" + "="*60)
        print("Test 2: Server Information")
        print("="*60)

        try:
            response = requests.get(f"{self.base_url}/info", timeout=10)

            if response.status_code != 200:
                print_error(f"Status code: {response.status_code}")
                self.failed += 1
                return False

            data = response.json()
            print_info(f"Model: {data.get('model_id')}")
            print_info(f"Device: {data.get('device')}")
            print_info(f"Topics: {', '.join(data.get('topics', []))}")
            print_info(f"Difficulties: {', '.join(data.get('difficulties', []))}")

            if "gpu_info" in data and data["gpu_info"]:
                print_info("GPU Information:")
                for key, value in data["gpu_info"].items():
                    print(f"  {key}: {value}")

            print_success("Server info retrieved successfully")
            self.passed += 1
            return True

        except requests.exceptions.RequestException as e:
            print_error(f"Request failed: {e}")
            self.failed += 1
            return False

    def test_single_classification(self) -> bool:
        """Test single question classification"""
        print("\n" + "="*60)
        print("Test 3: Single Question Classification")
        print("="*60)

        test_question = {
            "qid": "TEST1",
            "stem": "Solve the linear inequality 3x + 8 < 17",
            "options": ["x<1", "x<2", "x<3", "x<4"]
        }

        print_info(f"Question: {test_question['stem']}")

        try:
            response = requests.post(
                f"{self.base_url}/classify",
                json=test_question,
                headers=self.headers,
                timeout=30
            )

            if response.status_code == 401:
                print_error("Authentication failed - check API key")
                self.failed += 1
                return False

            if response.status_code != 200:
                print_error(f"Status code: {response.status_code}")
                print_error(f"Response: {response.text}")
                self.failed += 1
                return False

            data = response.json()
            print_info(f"Classification: {json.dumps(data, indent=2)}")

            # Validate response
            if data.get("topic") not in ["algebra", "calculus", "discrete", "geometry"]:
                print_error(f"Invalid topic: {data.get('topic')}")
                self.failed += 1
                return False

            if data.get("difficulty") not in ["E", "M", "H"]:
                print_error(f"Invalid difficulty: {data.get('difficulty')}")
                self.failed += 1
                return False

            print_success(f"Classified as: {data['topic']} ({data['difficulty']})")
            if data.get("confidence"):
                print_info(f"Confidence: {data['confidence']:.2f}")

            self.passed += 1
            return True

        except requests.exceptions.RequestException as e:
            print_error(f"Request failed: {e}")
            self.failed += 1
            return False

    def test_batch_routing(self) -> bool:
        """Test batch question routing (MCP endpoint)"""
        print("\n" + "="*60)
        print("Test 4: Batch Question Routing (MCP)")
        print("="*60)

        test_questions = [
            {
                "qid": "Q1",
                "stem": "Solve the equation 3x + 8 = 17",
                "options": ["x=1", "x=2", "x=3", "x=4"]
            },
            {
                "qid": "Q2",
                "stem": "Find the derivative of f(x) = x^2 + 3x",
                "options": ["2x+3", "x+3", "2x", "3"]
            },
            {
                "qid": "Q3",
                "stem": "How many ways can you arrange 5 books on a shelf?",
                "options": ["20", "60", "120", "240"]
            },
            {
                "qid": "Q4",
                "stem": "Find the area of a circle with radius 5",
                "options": ["25π", "10π", "5π", "15π"]
            }
        ]

        payload = {
            "tool": "route_questions",
            "inputs": test_questions
        }

        print_info(f"Routing {len(test_questions)} questions...")

        try:
            start_time = time.time()
            response = requests.post(
                f"{self.base_url}/mcp",
                json=payload,
                headers=self.headers,
                timeout=60
            )
            elapsed_time = time.time() - start_time

            if response.status_code == 401:
                print_error("Authentication failed - check API key")
                self.failed += 1
                return False

            if response.status_code != 200:
                print_error(f"Status code: {response.status_code}")
                print_error(f"Response: {response.text}")
                self.failed += 1
                return False

            results = response.json()

            if not isinstance(results, list):
                print_error("Response is not a list")
                self.failed += 1
                return False

            if len(results) != len(test_questions):
                print_error(f"Expected {len(test_questions)} results, got {len(results)}")
                self.failed += 1
                return False

            print_info("\nRouting Results:")
            print("-" * 60)

            topic_counts = {}
            for result in results:
                qid = result.get("qid")
                topic = result.get("topic")
                diff = result.get("difficulty")
                conf = result.get("confidence", 0)

                print(f"{qid}: {topic:10} ({diff}) - confidence: {conf:.2f}")

                topic_counts[topic] = topic_counts.get(topic, 0) + 1

                # Validate
                if topic not in ["algebra", "calculus", "discrete", "geometry"]:
                    print_error(f"  Invalid topic for {qid}: {topic}")
                    self.failed += 1
                    return False

                if diff not in ["E", "M", "H"]:
                    print_error(f"  Invalid difficulty for {qid}: {diff}")
                    self.failed += 1
                    return False

            print("-" * 60)
            print_info(f"Time taken: {elapsed_time:.2f} seconds")
            print_info(f"Questions/second: {len(test_questions)/elapsed_time:.2f}")
            print_info(f"Topic distribution: {topic_counts}")

            print_success(f"Batch routing completed successfully")
            self.passed += 1
            return True

        except requests.exceptions.RequestException as e:
            print_error(f"Request failed: {e}")
            self.failed += 1
            return False

    def test_error_handling(self) -> bool:
        """Test error handling"""
        print("\n" + "="*60)
        print("Test 5: Error Handling")
        print("="*60)

        # Test invalid tool name
        print_info("Testing invalid tool name...")
        try:
            response = requests.post(
                f"{self.base_url}/mcp",
                json={"tool": "invalid_tool", "inputs": []},
                headers=self.headers,
                timeout=10
            )

            if response.status_code == 400:
                print_success("Invalid tool name correctly rejected")
            else:
                print_warning(f"Expected 400, got {response.status_code}")
        except Exception as e:
            print_error(f"Test failed: {e}")
            self.failed += 1
            return False

        # Test empty inputs
        print_info("Testing empty inputs...")
        try:
            response = requests.post(
                f"{self.base_url}/mcp",
                json={"tool": "route_questions", "inputs": []},
                headers=self.headers,
                timeout=10
            )

            if response.status_code == 400:
                print_success("Empty inputs correctly rejected")
            else:
                print_warning(f"Expected 400, got {response.status_code}")
        except Exception as e:
            print_error(f"Test failed: {e}")

        # Test malformed request
        print_info("Testing malformed request...")
        try:
            response = requests.post(
                f"{self.base_url}/mcp",
                json={"invalid": "data"},
                headers=self.headers,
                timeout=10
            )

            if response.status_code in [400, 422]:
                print_success("Malformed request correctly rejected")
            else:
                print_warning(f"Expected 400/422, got {response.status_code}")
        except Exception as e:
            print_error(f"Test failed: {e}")

        self.passed += 1
        return True

    def run_all_tests(self):
        """Run all tests"""
        print("\n" + "="*60)
        print("MCP Router Service - Test Suite")
        print("="*60)
        print_info(f"Testing endpoint: {self.base_url}")
        if self.api_key:
            print_info("API key authentication: enabled")
        else:
            print_warning("API key authentication: disabled")

        # Run tests
        self.test_health()
        self.test_info()
        self.test_single_classification()
        self.test_batch_routing()
        self.test_error_handling()

        # Summary
        print("\n" + "="*60)
        print("Test Summary")
        print("="*60)
        total = self.passed + self.failed
        print(f"Total tests:  {total}")
        print(f"{GREEN}Passed:       {self.passed}{RESET}")
        print(f"{RED}Failed:       {self.failed}{RESET}")

        if self.failed == 0:
            print(f"\n{GREEN}All tests passed! ✓{RESET}")
            return 0
        else:
            print(f"\n{RED}Some tests failed ✗{RESET}")
            return 1

def main():
    import argparse

    parser = argparse.ArgumentParser(description="Test MCP Router Service")
    parser.add_argument(
        "--url",
        default="http://localhost:7001",
        help="Base URL of the MCP service"
    )
    parser.add_argument(
        "--api-key",
        default=None,
        help="API key for authentication (if required)"
    )

    args = parser.parse_args()

    tester = MCPTester(base_url=args.url, api_key=args.api_key)
    exit_code = tester.run_all_tests()
    sys.exit(exit_code)

if __name__ == "__main__":
    main()
