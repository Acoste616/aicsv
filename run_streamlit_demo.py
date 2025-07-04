#!/usr/bin/env python3
"""
Demo script to run the Streamlit Multimodal Content Analysis Platform
"""

import os
import sys
import subprocess
from pathlib import Path

def check_dependencies():
    """Check if required dependencies are installed"""
    try:
        import streamlit
        import pandas
        import plotly
        import wordcloud
        import openpyxl
        print("✅ All core dependencies are installed")
        return True
    except ImportError as e:
        print(f"❌ Missing dependency: {e}")
        return False

def check_sample_data():
    """Check if sample data exists"""
    if Path("sample_data.csv").exists():
        print("✅ Sample data found: sample_data.csv")
        return True
    else:
        print("❌ Sample data not found")
        return False

def main():
    """Main demo function"""
    print("🚀 Streamlit Multimodal Content Analysis Platform Demo")
    print("=" * 60)
    
    # Check dependencies
    if not check_dependencies():
        print("\n📦 Installing dependencies...")
        try:
            subprocess.check_call([
                sys.executable, "-m", "pip", "install", "--break-system-packages",
                "streamlit", "pandas", "plotly", "wordcloud", "openpyxl"
            ])
            print("✅ Dependencies installed successfully!")
        except subprocess.CalledProcessError:
            print("❌ Failed to install dependencies")
            return False
    
    # Check sample data
    if not check_sample_data():
        print("\n📊 Creating sample data...")
        import pandas as pd
        from datetime import datetime
        
        data = {
            'url': [
                'https://github.com/microsoft/vscode',
                'https://docs.python.org/3/',
                'https://stackoverflow.com/questions/tagged/python',
                'https://medium.com/@author/ai-article',
                'https://arxiv.org/abs/2301.00001'
            ],
            'content': [
                'Microsoft Visual Studio Code editor',
                'Python Documentation',
                'Python questions on Stack Overflow',
                'AI and Machine Learning Article',
                'Research Paper on AI'
            ],
            'rawContent': [
                'Check out this awesome code editor',
                'Learn Python programming',
                'Great resource for Python help',
                'Interesting insights into AI development',
                'Latest research in artificial intelligence'
            ],
            'created_date': [
                '2024-01-15T10:30:00Z',
                '2024-01-15T11:00:00Z',
                '2024-01-15T11:30:00Z',
                '2024-01-15T12:00:00Z',
                '2024-01-15T12:30:00Z'
            ]
        }
        
        df = pd.DataFrame(data)
        df.to_csv('sample_data.csv', index=False)
        print("✅ Sample data created")
    
    # Launch Streamlit
    print("\n🌐 Launching Streamlit application...")
    print("📋 Instructions:")
    print("1. The application will open in your browser at http://localhost:8501")
    print("2. Upload the sample_data.csv file or your own CSV")
    print("3. Choose an LLM provider (recommend 'Mistral 7B (Local)' for testing)")
    print("4. Configure processing settings and start analysis")
    print("5. Explore the Dashboard, Results, and Export features")
    print("\n💡 Tips:")
    print("- Use 'Mistral 7B (Local)' for free processing (no API key needed)")
    print("- Check the Dashboard for visualizations after processing")
    print("- Export results to JSON, Excel, or CSV formats")
    print("\n🔄 To stop the application, press Ctrl+C in this terminal")
    print("=" * 60)
    
    try:
        # Add local bin to PATH for streamlit command
        local_bin = os.path.expanduser("~/.local/bin")
        current_path = os.environ.get("PATH", "")
        if local_bin not in current_path:
            os.environ["PATH"] = f"{local_bin}:{current_path}"
        
        # Run streamlit
        subprocess.run([
            sys.executable, "-m", "streamlit", "run", "streamlit_app.py",
            "--server.port", "8501",
            "--server.headless", "true"
        ])
    except KeyboardInterrupt:
        print("\n\n👋 Streamlit application stopped")
    except Exception as e:
        print(f"\n❌ Error running Streamlit: {e}")
        print("\n🔧 Try running manually:")
        print("python3 -m streamlit run streamlit_app.py")

if __name__ == "__main__":
    main()