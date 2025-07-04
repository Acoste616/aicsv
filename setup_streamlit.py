#!/usr/bin/env python3
"""
Setup script for Streamlit Multimodal Content Analysis Platform
Installs all necessary dependencies and provides setup instructions.
"""

import subprocess
import sys
import os

def install_dependencies():
    """Install all required dependencies"""
    print("🔧 Installing dependencies...")
    
    try:
        # Install requirements
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
        print("✅ Dependencies installed successfully!")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Error installing dependencies: {e}")
        return False

def create_sample_data():
    """Create sample CSV data for testing"""
    print("📊 Creating sample data...")
    
    sample_data = """url,content,rawContent,created_date
https://github.com/microsoft/vscode,Microsoft Visual Studio Code editor,Check out this awesome code editor,2024-01-15T10:30:00Z
https://docs.python.org/3/,Python Documentation,Learn Python programming,2024-01-15T11:00:00Z
https://stackoverflow.com/questions/tagged/python,Python questions on Stack Overflow,Great resource for Python help,2024-01-15T11:30:00Z
https://medium.com/@author/ai-article,AI and Machine Learning Article,Interesting insights into AI development,2024-01-15T12:00:00Z
https://arxiv.org/abs/2301.00001,Research Paper on AI,Latest research in artificial intelligence,2024-01-15T12:30:00Z
"""
    
    try:
        with open("sample_data.csv", "w", encoding="utf-8") as f:
            f.write(sample_data)
        print("✅ Sample data created: sample_data.csv")
        return True
    except Exception as e:
        print(f"❌ Error creating sample data: {e}")
        return False

def check_system_requirements():
    """Check if system meets requirements"""
    print("🔍 Checking system requirements...")
    
    # Check Python version
    if sys.version_info < (3, 8):
        print("❌ Python 3.8 or higher is required")
        return False
    
    print(f"✅ Python {sys.version.split()[0]} detected")
    
    # Check if streamlit is available
    try:
        import streamlit
        print(f"✅ Streamlit {streamlit.__version__} is available")
    except ImportError:
        print("⚠️  Streamlit not found - will be installed")
    
    return True

def main():
    """Main setup function"""
    print("🚀 Streamlit Multimodal Content Analysis Platform Setup")
    print("=" * 60)
    
    # Check system requirements
    if not check_system_requirements():
        print("\n❌ System requirements not met. Please upgrade Python.")
        return False
    
    # Install dependencies
    if not install_dependencies():
        print("\n❌ Failed to install dependencies. Please check your internet connection.")
        return False
    
    # Create sample data
    if not create_sample_data():
        print("\n⚠️  Failed to create sample data, but you can still use your own CSV files.")
    
    # Success message
    print("\n" + "=" * 60)
    print("🎉 Setup completed successfully!")
    print("\n📋 Next steps:")
    print("1. Run the Streamlit app:")
    print("   streamlit run streamlit_app.py")
    print("\n2. Open your browser and navigate to:")
    print("   http://localhost:8501")
    print("\n3. Upload your CSV file or use the sample data:")
    print("   - sample_data.csv (created for testing)")
    print("   - Your CSV should have columns: url, content, rawContent")
    print("\n4. Select your LLM provider and start processing!")
    print("\n💡 Tips:")
    print("- Use local models (Mistral, Ollama) for free processing")
    print("- Cloud models (OpenAI, Anthropic) provide higher quality but cost money")
    print("- Enable OCR and thread collection for comprehensive analysis")
    print("- Check the Dashboard for analytics and visualizations")
    print("- Export results to JSON, Excel, or CSV formats")
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)