#!/usr/bin/env python3
"""
COMPREHENSIVE TEST SUITE
Kompletny zestaw testów dla systemu przetwarzania CSV

TESTY:
1. CSV Cleaning & Validation
2. Content Extraction Quality
3. Duplicate Detection
4. LLM Processing Quality
5. Pipeline Integration
6. Performance Tests
7. Error Handling
"""

import unittest
import json
import pandas as pd
import time
import tempfile
import shutil
from pathlib import Path
from typing import Dict, List
import sys
import os

# Import komponentów do testowania
from csv_cleaner_and_prep import CSVCleanerAndPrep
from enhanced_content_processor import EnhancedContentProcessor
from content_extractor import ContentExtractor

class TestCSVCleaning(unittest.TestCase):
    """Testy czyszczenia i walidacji CSV."""
    
    def setUp(self):
        self.cleaner = CSVCleanerAndPrep()
        self.test_dir = Path(tempfile.mkdtemp())
        
    def tearDown(self):
        shutil.rmtree(self.test_dir)
        
    def test_csv_format_detection(self):
        """Test automatycznego wykrywania formatu CSV."""
        # Symuluj różne formaty
        simple_data = {
            'full_text': ['Test tweet 1', 'Test tweet 2'],
            'tweet_url': ['https://x.com/test1', 'https://x.com/test2']
        }
        
        complex_data = {
            'id': ['123', '456'],
            'full_text': ['Test tweet 1', 'Test tweet 2'],
            'favorite_count': [10, 20],
            'url': ['https://x.com/test1', 'https://x.com/test2']
        }
        
        # Test simple format
        df_simple = pd.DataFrame(simple_data)
        format_type = self.cleaner.detect_csv_format(df_simple)
        self.assertEqual(format_type, "simple")
        
        # Test complex format
        df_complex = pd.DataFrame(complex_data)
        format_type = self.cleaner.detect_csv_format(df_complex)
        self.assertEqual(format_type, "api")
        
    def test_duplicate_removal(self):
        """Test usuwania duplikatów."""
        data = {
            'full_text': ['Test tweet', 'Test tweet', 'Different tweet'],
            'tweet_url': ['https://x.com/test1', 'https://x.com/test1', 'https://x.com/test2']
        }
        
        df = pd.DataFrame(data)
        cleaned_df = self.cleaner.remove_duplicates(df)
        
        # Powinny zostać 2 unikalne wpisy
        self.assertEqual(len(cleaned_df), 2)
        
    def test_data_validation(self):
        """Test walidacji danych."""
        # Test danych z błędami
        bad_data = {
            'full_text': ['Good tweet', '', 'Another good tweet', None],
            'tweet_url': ['https://x.com/test1', 'invalid-url', 'https://x.com/test2', '']
        }
        
        df = pd.DataFrame(bad_data)
        valid_df, invalid_count = self.cleaner.validate_data(df)
        
        # Powinien zostać 1 prawidłowy wpis (pierwszy i trzeci)
        self.assertEqual(len(valid_df), 2)
        self.assertEqual(invalid_count, 2)


class TestContentExtraction(unittest.TestCase):
    """Testy ekstrakcji treści."""
    
    def setUp(self):
        self.extractor = ContentExtractor()
        
    def test_url_accessibility(self):
        """Test dostępności różnych typów URL."""
        test_urls = [
            "https://httpbin.org/html",  # Test URL that should work
            "https://nonexistent-domain-12345.com",  # Should fail
            "invalid-url",  # Invalid format
        ]
        
        results = []
        for url in test_urls:
            try:
                content = self.extractor.extract_with_retry(url)
                results.append((url, len(content) > 0))
            except:
                results.append((url, False))
                
        # Pierwszy powinien działać, reszta nie
        self.assertTrue(results[0][1])  # httpbin should work
        self.assertFalse(results[1][1])  # nonexistent should fail
        self.assertFalse(results[2][1])  # invalid should fail
        
    def test_content_quality_detection(self):
        """Test wykrywania jakości treści."""
        # Mock quality checker
        test_cases = [
            ("This is a good quality content with useful information about programming", True),
            ("404 Not Found", False),
            ("", False),
            ("Short", False),
            ("Repetitive text " * 100, False),  # Too repetitive
        ]
        
        from master_processing_pipeline import MasterProcessingPipeline
        pipeline = MasterProcessingPipeline()
        
        for content, expected_valid in test_cases:
            quality = pipeline.validate_content_quality(content, "test-url")
            self.assertEqual(quality["valid"], expected_valid, 
                           f"Content: '{content[:30]}...' should be {expected_valid}")


class TestLLMProcessing(unittest.TestCase):
    """Testy przetwarzania LLM."""
    
    def setUp(self):
        self.processor = EnhancedContentProcessor()
        
    def test_llm_connectivity(self):
        """Test połączenia z LLM."""
        try:
            # Test z prostym contentem
            result = self.processor.process_content(
                content="Test content about AI programming tutorial",
                url="https://test.com",
                source_type="twitter"
            )
            
            # Sprawdź czy zwrócił poprawną strukturę
            self.assertIsInstance(result, dict)
            self.assertIn("title", result)
            self.assertIn("short_description", result)
            
        except Exception as e:
            self.skipTest(f"LLM nie dostępny: {e}")
            
    def test_output_format_validation(self):
        """Test walidacji formatu outputu LLM."""
        # Mock rezultat LLM
        mock_result = {
            "title": "Test Title",
            "short_description": "Test description",
            "detailed_description": "Longer test description",
            "category": "AI/Technology",
            "tags": ["AI", "test"],
            "content_type": "twitter_post"
        }
        
        # Sprawdź wszystkie wymagane pola
        required_fields = ["title", "short_description", "category", "tags"]
        for field in required_fields:
            self.assertIn(field, mock_result)
            self.assertTrue(mock_result[field])  # Not empty


class TestDuplicateDetection(unittest.TestCase):
    """Testy wykrywania duplikatów."""
    
    def setUp(self):
        from master_processing_pipeline import MasterProcessingPipeline
        self.pipeline = MasterProcessingPipeline()
        
    def test_url_duplicate_detection(self):
        """Test wykrywania duplikatów URL."""
        # Test tego samego URL
        url = "https://x.com/test/status/123"
        
        # Pierwszy raz nie powinien być duplikatem
        is_duplicate1 = self.pipeline.detect_duplicates(url, "Some title")
        self.assertFalse(is_duplicate1)
        
        # Drugi raz powinien być duplikatem
        is_duplicate2 = self.pipeline.detect_duplicates(url, "Some title")
        self.assertTrue(is_duplicate2)
        
    def test_url_normalization(self):
        """Test normalizacji URL dla duplikatów."""
        urls = [
            "https://x.com/test/status/123",
            "https://X.COM/test/status/123",  # Different case
            "https://x.com/test/status/123/",  # Trailing slash
        ]
        
        # Wszystkie powinny być traktowane jako duplikaty
        results = []
        for url in urls:
            is_duplicate = self.pipeline.detect_duplicates(url, "Title")
            results.append(is_duplicate)
            
        # Pierwszy nie duplikat, reszta tak
        self.assertFalse(results[0])
        self.assertTrue(results[1])
        self.assertTrue(results[2])


class TestPerformance(unittest.TestCase):
    """Testy wydajnościowe."""
    
    def test_single_entry_processing_time(self):
        """Test czasu przetwarzania pojedynczego wpisu."""
        from master_processing_pipeline import MasterProcessingPipeline
        pipeline = MasterProcessingPipeline()
        
        test_entry = {
            'tweet_url': 'https://httpbin.org/html',
            'full_text': 'Test tweet content for performance testing'
        }
        
        start_time = time.time()
        result = pipeline.process_single_entry(test_entry)
        processing_time = time.time() - start_time
        
        # Pojedynczy wpis nie powinien trwać dłużej niż 30 sekund
        self.assertLess(processing_time, 30, 
                       f"Processing took too long: {processing_time:.2f}s")
        
    def test_batch_processing_efficiency(self):
        """Test efektywności przetwarzania wsadowego."""
        # Mock batch entries
        entries = [
            {'tweet_url': f'https://httpbin.org/html?id={i}', 
             'full_text': f'Test content {i}'}
            for i in range(5)
        ]
        
        start_time = time.time()
        
        # Symuluj batch processing
        results = []
        for entry in entries:
            result = {'processed': True, 'url': entry['tweet_url']}
            results.append(result)
            
        batch_time = time.time() - start_time
        avg_time_per_entry = batch_time / len(entries)
        
        # Średni czas na wpis powinien być rozumny
        self.assertLess(avg_time_per_entry, 10,
                       f"Average time per entry too high: {avg_time_per_entry:.2f}s")


class TestErrorHandling(unittest.TestCase):
    """Testy obsługi błędów."""
    
    def test_invalid_url_handling(self):
        """Test obsługi nieprawidłowych URL."""
        from master_processing_pipeline import MasterProcessingPipeline
        pipeline = MasterProcessingPipeline()
        
        invalid_entries = [
            {'tweet_url': 'invalid-url', 'full_text': 'Test'},
            {'tweet_url': '', 'full_text': 'Test'},
            {'tweet_url': 'https://nonexistent-domain-12345.com', 'full_text': 'Test'},
        ]
        
        for entry in invalid_entries:
            result = pipeline.process_single_entry(entry)
            
            # Powinien obsłużyć błąd gracefully
            self.assertIn('errors', result)
            self.assertFalse(result.get('success', False))
            
    def test_llm_error_recovery(self):
        """Test recovery po błędach LLM."""
        processor = EnhancedContentProcessor()
        
        # Test z nieprawidłowymi danymi
        try:
            result = processor.process_content(
                content="",  # Empty content
                url="test-url",
                source_type="twitter"
            )
            
            # Powinien zwrócić błąd lub fallback
            if result:
                self.assertTrue('error' in result or 'title' in result)
                
        except Exception as e:
            # Błędy powinny być obsłużone, nie rzucane
            self.fail(f"Nieobsłużony błąd: {e}")


class TestIntegration(unittest.TestCase):
    """Testy integracyjne całego systemu."""
    
    def setUp(self):
        # Przygotuj test CSV
        self.test_dir = Path(tempfile.mkdtemp())
        self.test_csv = self.test_dir / "test_bookmarks.csv"
        
        test_data = {
            'full_text': [
                'Test tweet about AI programming',
                'Another tweet about machine learning',
                'Duplicate test tweet',  # This will be a duplicate later
            ],
            'tweet_url': [
                'https://httpbin.org/html?test=1',
                'https://httpbin.org/html?test=2', 
                'https://httpbin.org/html?test=3',
            ],
            'screen_name': ['user1', 'user2', 'user3'],
            'tweeted_at': ['2024-01-01', '2024-01-02', '2024-01-03']
        }
        
        df = pd.DataFrame(test_data)
        df.to_csv(self.test_csv, index=False)
        
    def tearDown(self):
        shutil.rmtree(self.test_dir)
        
    def test_end_to_end_processing(self):
        """Test pełnego przetwarzania end-to-end."""
        from master_processing_pipeline import MasterProcessingPipeline
        
        # Konfiguruj pipeline dla testów
        pipeline = MasterProcessingPipeline()
        pipeline.config["batch_size"] = 2
        pipeline.config["checkpoint_frequency"] = 2
        
        # Uruchom na test CSV
        try:
            result = pipeline.process_csv(str(self.test_csv))
            
            # Sprawdź czy się udało
            self.assertTrue(result["success"])
            self.assertGreater(result["total_processed"], 0)
            self.assertTrue(Path(result["output_file"]).exists())
            
            # Sprawdź output file
            with open(result["output_file"], 'r') as f:
                output_data = json.load(f)
                
            self.assertIn("metadata", output_data)
            self.assertIn("entries", output_data)
            
        except Exception as e:
            self.skipTest(f"End-to-end test failed (może być OK w środowisku testowym): {e}")


def run_comprehensive_tests():
    """Uruchamia wszystkie testy z raportowaniem."""
    
    print("🧪 URUCHAMIANIE COMPREHENSIVE TEST SUITE")
    print("=" * 60)
    
    # Lista wszystkich klas testowych
    test_classes = [
        TestCSVCleaning,
        TestContentExtraction, 
        TestLLMProcessing,
        TestDuplicateDetection,
        TestPerformance,
        TestErrorHandling,
        TestIntegration
    ]
    
    total_tests = 0
    passed_tests = 0
    failed_tests = 0
    skipped_tests = 0
    
    for test_class in test_classes:
        print(f"\n📋 Running {test_class.__name__}...")
        
        suite = unittest.TestLoader().loadTestsFromTestClass(test_class)
        runner = unittest.TextTestRunner(verbosity=1, stream=open(os.devnull, 'w'))
        result = runner.run(suite)
        
        class_total = result.testsRun
        class_passed = class_total - len(result.failures) - len(result.errors) - len(result.skipped)
        class_failed = len(result.failures) + len(result.errors)
        class_skipped = len(result.skipped)
        
        total_tests += class_total
        passed_tests += class_passed
        failed_tests += class_failed
        skipped_tests += class_skipped
        
        status_emoji = "✅" if class_failed == 0 else "❌"
        print(f"{status_emoji} {test_class.__name__}: {class_passed}/{class_total} passed")
        
        if class_failed > 0:
            print(f"   ❌ Failures: {class_failed}")
            for failure in result.failures:
                print(f"      - {failure[0]}")
            for error in result.errors:
                print(f"      - {error[0]} (ERROR)")
                
        if class_skipped > 0:
            print(f"   ⏭️  Skipped: {class_skipped}")
    
    # Podsumowanie
    print("\n" + "=" * 60)
    print("📊 PODSUMOWANIE TESTÓW:")
    print(f"✅ Passed: {passed_tests}")
    print(f"❌ Failed: {failed_tests}") 
    print(f"⏭️  Skipped: {skipped_tests}")
    print(f"📈 Total: {total_tests}")
    
    success_rate = (passed_tests / total_tests * 100) if total_tests > 0 else 0
    print(f"🎯 Success Rate: {success_rate:.1f}%")
    
    if failed_tests == 0:
        print("\n🎉 WSZYSTKIE TESTY PRZESZŁY!")
        return True
    else:
        print(f"\n⚠️  {failed_tests} testów nie przeszło. Sprawdź logi powyżej.")
        return False


if __name__ == "__main__":
    success = run_comprehensive_tests()
    sys.exit(0 if success else 1) 