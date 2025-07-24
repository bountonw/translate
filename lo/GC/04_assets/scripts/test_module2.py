#!/usr/bin/env python3
"""
Test Suite for Module 2: Dictionary Lookup and Line-Breaking Application

This test script validates the complete functionality of module2_preprocess.py
to ensure we don't break file handling or processing capabilities during development.

USAGE:
python3 test_module2.py

COVERAGE:
- Input file reading
- Output file generation  
- Function definitions and imports
- End-to-end pipeline processing
- Debug mode functionality
- Error handling
"""

import os
import sys
import subprocess
import tempfile
from pathlib import Path
from typing import Dict, List, Any
import shutil

class Module2Tester:
    def __init__(self):
        self.script_dir = Path(__file__).parent
        self.project_root = self.script_dir.parent.parent
        self.temp_dir = self.project_root / "04_assets" / "temp"
        self.module2_script = self.script_dir / "module2_preprocess.py"
        self.test_input = "GC01"
        self.results = []
        
    def log_result(self, test_name: str, passed: bool, message: str = ""):
        """Log test result."""
        status = "✓ PASS" if passed else "✗ FAIL"
        self.results.append((test_name, passed, message))
        print(f"{status}: {test_name}")
        if message and not passed:
            print(f"    {message}")
    
    def test_module_imports(self) -> bool:
        """Test that the module can be imported and key functions exist."""
        try:
            # Add the scripts directory to Python path
            sys.path.insert(0, str(self.script_dir))
            import module2_preprocess
            
            # Check for key functions
            required_functions = [
                'parse_longest_first',
                'parse_shortest_first', 
                'parse_with_backtrack',
                'process_file',
                'LaoDictionary',
                'is_invalid_standalone_lao'
            ]
            
            missing_functions = []
            for func_name in required_functions:
                if not hasattr(module2_preprocess, func_name):
                    missing_functions.append(func_name)
            
            if missing_functions:
                self.log_result("Module imports", False, f"Missing functions: {missing_functions}")
                return False
            else:
                self.log_result("Module imports", True)
                return True
                
        except Exception as e:
            self.log_result("Module imports", False, f"Import error: {e}")
            return False
    
    def test_input_file_exists(self) -> bool:
        """Test that the required input file exists."""
        # Look for stage1 file (debug mode input)
        stage1_file = self.temp_dir / f"{self.test_input}_lo_stage1.tmp"
        regular_file = self.temp_dir / f"{self.test_input}_lo.tmp"
        
        if stage1_file.exists():
            self.log_result("Input file exists", True, f"Found: {stage1_file.name}")
            return True
        elif regular_file.exists():
            self.log_result("Input file exists", True, f"Found: {regular_file.name}")
            return True
        else:
            self.log_result("Input file exists", False, f"Neither {stage1_file.name} nor {regular_file.name} found")
            return False
    
    def test_input_file_readable(self) -> bool:
        """Test that input file can be read and contains expected content."""
        try:
            stage1_file = self.temp_dir / f"{self.test_input}_lo_stage1.tmp"
            regular_file = self.temp_dir / f"{self.test_input}_lo.tmp"
            
            input_file = stage1_file if stage1_file.exists() else regular_file
            
            with open(input_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Basic validation - should contain Lao text and TeX commands
            has_lao = any('\u0e80' <= char <= '\u0eff' for char in content)
            has_tex_commands = any(cmd in content for cmd in ['\\lw{', '\\nodict{', '\\section'])
            
            if has_lao and len(content) > 100:  # Reasonable content size
                self.log_result("Input file readable", True, f"File size: {len(content)} chars, has Lao: {has_lao}")
                return True
            else:
                self.log_result("Input file readable", False, f"Content validation failed - size: {len(content)}, has Lao: {has_lao}")
                return False
                
        except Exception as e:
            self.log_result("Input file readable", False, f"Read error: {e}")
            return False
    
    def test_dictionary_loading(self) -> bool:
        """Test that the dictionary can be loaded."""
        try:
            sys.path.insert(0, str(self.script_dir))
            from module2_preprocess import LaoDictionary, get_dictionary_path
            
            dict_path = get_dictionary_path()
            dictionary = LaoDictionary(dict_path)
            
            term_count = len(dictionary.terms)
            if term_count > 1000:  # Reasonable dictionary size
                self.log_result("Dictionary loading", True, f"Loaded {term_count} terms")
                return True
            else:
                self.log_result("Dictionary loading", False, f"Dictionary too small: {term_count} terms")
                return False
                
        except Exception as e:
            self.log_result("Dictionary loading", False, f"Dictionary load error: {e}")
            return False
    
    def test_parsing_functions(self) -> bool:
        """Test that parsing functions work with sample text."""
        try:
            sys.path.insert(0, str(self.script_dir))
            from module2_preprocess import (
                parse_longest_first, parse_shortest_first, parse_with_backtrack,
                LaoDictionary, get_dictionary_path
            )
            
            # Load dictionary
            dict_path = get_dictionary_path()
            dictionary = LaoDictionary(dict_path)
            
            # Test with simple Lao text
            test_text = "ການສຶກສາ"
            
            # Test each parsing function
            parsers = [
                ("longest-first", parse_longest_first),
                ("shortest-first", parse_shortest_first),
                ("backtrack", parse_with_backtrack)
            ]
            
            for parser_name, parser_func in parsers:
                try:
                    result = parser_func(test_text, dictionary, debug=False)
                    if isinstance(result, list) and len(result) > 0:
                        self.log_result(f"Parser {parser_name}", True)
                    else:
                        self.log_result(f"Parser {parser_name}", False, "Empty or invalid result")
                        return False
                except Exception as e:
                    self.log_result(f"Parser {parser_name}", False, f"Parser error: {e}")
                    return False
            
            return True
            
        except Exception as e:
            self.log_result("Parsing functions", False, f"Setup error: {e}")
            return False
    
    def test_debug_mode_processing(self) -> bool:
        """Test end-to-end processing in debug mode."""
        try:
            # Clean up any existing output first
            stage2_file = self.temp_dir / f"{self.test_input}_lo_stage2.tmp"
            if stage2_file.exists():
                stage2_file.unlink()
            
            # Run module2 in debug mode
            cmd = [
                sys.executable, 
                str(self.module2_script), 
                self.test_input, 
                "--debug"
            ]
            
            # Change to project root directory (required by module)
            result = subprocess.run(
                cmd, 
                cwd=self.project_root,
                capture_output=True, 
                text=True, 
                timeout=60
            )
            
            # Check command execution
            if result.returncode != 0:
                self.log_result("Debug mode processing", False, f"Command failed: {result.stderr}")
                return False
            
            # Check output file was created
            if not stage2_file.exists():
                self.log_result("Debug mode processing", False, "Stage2 output file not created")
                return False
            
            # Check output file has content
            with open(stage2_file, 'r', encoding='utf-8') as f:
                output_content = f.read()
            
            if len(output_content) < 100:
                self.log_result("Debug mode processing", False, f"Output file too small: {len(output_content)} chars")
                return False
            
            # Check for expected processing markers
            has_lw_commands = '\\lw{' in output_content
            has_processing = has_lw_commands or '\\nodict{' in output_content
            
            if has_processing:
                self.log_result("Debug mode processing", True, f"Output: {len(output_content)} chars, processed: {has_lw_commands}")
                return True
            else:
                self.log_result("Debug mode processing", False, "No processing markers found in output")
                return False
                
        except subprocess.TimeoutExpired:
            self.log_result("Debug mode processing", False, "Command timeout")
            return False
        except Exception as e:
            self.log_result("Debug mode processing", False, f"Processing error: {e}")
            return False
    
    def test_output_file_content(self) -> bool:
        """Test that output file has expected structure and content."""
        try:
            stage2_file = self.temp_dir / f"{self.test_input}_lo_stage2.tmp"
            
            if not stage2_file.exists():
                self.log_result("Output file content", False, "Stage2 file does not exist")
                return False
            
            with open(stage2_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Content validation checks
            checks = [
                ("Has content", len(content) > 500),
                ("Has Lao text", any('\u0e80' <= char <= '\u0eff' for char in content)),
                ("Has TeX commands", any(cmd in content for cmd in ['\\lw{', '\\section', '\\source'])),
                ("Has processing", '\\lw{' in content or '\\nodict{' in content),
                ("No syntax errors", '\\lw{}' not in content and '\\nodict{}' not in content)
            ]
            
            all_passed = True
            for check_name, check_result in checks:
                if not check_result:
                    self.log_result(f"Content check: {check_name}", False)
                    all_passed = False
                else:
                    self.log_result(f"Content check: {check_name}", True)
            
            return all_passed
            
        except Exception as e:
            self.log_result("Output file content", False, f"Content check error: {e}")
            return False
    
    def test_debug_logs_generated(self) -> bool:
        """Test that debug mode generates expected log files."""
        try:
            log_files = [
                ("nodict_analysis.log", self.temp_dir / "nodict_analysis.log"),
                ("lookahead_decisions.log", self.temp_dir / "lookahead_decisions.log")
            ]
            
            all_logs_exist = True
            for log_name, log_path in log_files:
                if log_path.exists():
                    # Check file has content
                    with open(log_path, 'r', encoding='utf-8') as f:
                        log_content = f.read()
                    
                    if len(log_content) > 50:  # Reasonable log content
                        self.log_result(f"Debug log: {log_name}", True, f"Size: {len(log_content)} chars")
                    else:
                        self.log_result(f"Debug log: {log_name}", False, f"Log too small: {len(log_content)} chars")
                        all_logs_exist = False
                else:
                    # lookahead_decisions.log might not exist if no strategy changes occurred
                    if log_name == "lookahead_decisions.log":
                        self.log_result(f"Debug log: {log_name}", True, "No strategy changes (expected)")
                    else:
                        self.log_result(f"Debug log: {log_name}", False, "Log file missing")
                        all_logs_exist = False
            
            return all_logs_exist
            
        except Exception as e:
            self.log_result("Debug logs generated", False, f"Log check error: {e}")
            return False
    
    def test_error_handling(self) -> bool:
        """Test error handling with invalid input."""
        try:
            # Test with non-existent file
            cmd = [
                sys.executable, 
                str(self.module2_script), 
                "NONEXISTENT99", 
                "--debug"
            ]
            
            result = subprocess.run(
                cmd, 
                cwd=self.project_root,
                capture_output=True, 
                text=True, 
                timeout=30
            )
            
            # Should handle error gracefully (return code 1 but not crash)
            if result.returncode == 1 and "Could not find file" in result.stdout:
                self.log_result("Error handling", True, "Graceful error handling for missing file")
                return True
            else:
                self.log_result("Error handling", False, f"Unexpected error handling: rc={result.returncode}")
                return False
                
        except Exception as e:
            self.log_result("Error handling", False, f"Error test failed: {e}")
            return False
    
    def run_all_tests(self) -> bool:
        """Run all tests and return overall success."""
        print("=" * 60)
        print("MODULE 2 TEST SUITE")
        print("=" * 60)
        
        tests = [
            self.test_module_imports,
            self.test_input_file_exists,
            self.test_input_file_readable,
            self.test_dictionary_loading,
            self.test_parsing_functions,
            self.test_debug_mode_processing,
            self.test_output_file_content,
            self.test_debug_logs_generated,
            self.test_error_handling
        ]
        
        print(f"Running {len(tests)} tests...\n")
        
        for test in tests:
            test()
        
        # Summary
        print("\n" + "=" * 60)
        print("TEST SUMMARY")
        print("=" * 60)
        
        passed = sum(1 for _, success, _ in self.results if success)
        total = len(self.results)
        
        print(f"Passed: {passed}/{total} tests")
        
        if passed == total:
            print("🎉 ALL TESTS PASSED - Module 2 is stable for development")
            return True
        else:
            print("⚠️  SOME TESTS FAILED - Fix issues before making changes")
            print("\nFailed tests:")
            for test_name, success, message in self.results:
                if not success:
                    print(f"  ✗ {test_name}: {message}")
            return False

def main():
    """Run the test suite."""
    tester = Module2Tester()
    success = tester.run_all_tests()
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()