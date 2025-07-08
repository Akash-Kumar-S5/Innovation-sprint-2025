#!/usr/bin/env python3
"""
Setup script for Presidio Research Agent
Handles installation, configuration, and initialization
"""

import os
import sys
import subprocess
import json
import shutil
from pathlib import Path
import argparse
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class PresidioSetup:
    """
    Setup and configuration manager for Presidio Research Agent
    """
    
    def __init__(self, project_root: str = None):
        self.project_root = Path(project_root) if project_root else Path(__file__).parent
        self.requirements_file = self.project_root / "requirements.txt"
        self.env_example = self.project_root / ".env.example"
        self.env_file = self.project_root / ".env"
        
    def check_python_version(self):
        """Check if Python version is compatible"""
        if sys.version_info < (3, 8):
            logger.error("Python 3.8 or higher is required")
            return False
        
        logger.info(f"✅ Python {sys.version_info.major}.{sys.version_info.minor} detected")
        return True
    
    def install_python_dependencies(self):
        """Install Python dependencies"""
        try:
            logger.info("📦 Installing Python dependencies...")
            
            # Upgrade pip first
            subprocess.run([sys.executable, "-m", "pip", "install", "--upgrade", "pip"], 
                         check=True, capture_output=True)
            
            # Install requirements
            if self.requirements_file.exists():
                subprocess.run([sys.executable, "-m", "pip", "install", "-r", str(self.requirements_file)], 
                             check=True, capture_output=True)
                logger.info("✅ Python dependencies installed successfully")
            else:
                logger.warning("⚠️ requirements.txt not found, installing core dependencies...")
                core_deps = [
                    "langchain>=0.1.0",
                    "langchain-openai>=0.1.0",
                    "langchain-community>=0.3.0",
                    "langchain-chroma>=0.2.0",
                    "chromadb>=0.5.0",
                    "sentence-transformers>=2.2.0",
                    "fastapi>=0.100.0",
                    "uvicorn>=0.23.0",
                    "python-dotenv>=1.0.0",
                    "requests>=2.31.0",
                    "beautifulsoup4>=4.12.0"
                ]
                
                for dep in core_deps:
                    subprocess.run([sys.executable, "-m", "pip", "install", dep], 
                                 check=True, capture_output=True)
                
                logger.info("✅ Core dependencies installed")
            
            return True
            
        except subprocess.CalledProcessError as e:
            logger.error(f"❌ Failed to install Python dependencies: {e}")
            return False
    
    def setup_node_dependencies(self):
        """Setup Node.js dependencies for MCP server"""
        try:
            mcp_dir = self.project_root / "mcp-server"
            
            if not mcp_dir.exists():
                logger.warning("⚠️ MCP server directory not found")
                return True
            
            # Check if Node.js is available
            try:
                subprocess.run(["node", "--version"], check=True, capture_output=True)
                subprocess.run(["npm", "--version"], check=True, capture_output=True)
            except (subprocess.CalledProcessError, FileNotFoundError):
                logger.warning("⚠️ Node.js/npm not found. MCP server setup skipped.")
                logger.info("   Install Node.js from https://nodejs.org/ to enable Google Docs integration")
                return True
            
            logger.info("📦 Installing Node.js dependencies for MCP server...")
            
            # Change to MCP directory and install dependencies
            original_cwd = os.getcwd()
            os.chdir(mcp_dir)
            
            try:
                subprocess.run(["npm", "install"], check=True, capture_output=True)
                logger.info("✅ MCP server dependencies installed")
                return True
            finally:
                os.chdir(original_cwd)
                
        except subprocess.CalledProcessError as e:
            logger.error(f"❌ Failed to install Node.js dependencies: {e}")
            return False
    
    def create_directories(self):
        """Create necessary directories"""
        directories = [
            "data/hr-policies",
            "data/google-docs-credentials",
            "rag-system/chroma_db",
            "logs"
        ]
        
        for dir_path in directories:
            full_path = self.project_root / dir_path
            full_path.mkdir(parents=True, exist_ok=True)
            logger.info(f"📁 Created directory: {dir_path}")
        
        return True
    
    def setup_environment_file(self):
        """Setup environment configuration file"""
        if self.env_file.exists():
            logger.info("✅ .env file already exists")
            return True
        
        if self.env_example.exists():
            shutil.copy(self.env_example, self.env_file)
            logger.info("📝 Created .env file from template")
            logger.warning("⚠️ Please edit .env file with your actual configuration values")
        else:
            # Create basic .env file
            env_content = """# Presidio Research Agent Configuration
OPENAI_API_KEY=your_openai_api_key_here
API_HOST=0.0.0.0
API_PORT=8000
LOG_LEVEL=info
"""
            with open(self.env_file, 'w') as f:
                f.write(env_content)
            logger.info("📝 Created basic .env file")
        
        return True
    
    def setup_google_credentials(self):
        """Setup Google credentials template"""
        creds_dir = self.project_root / "data/google-docs-credentials"
        creds_file = creds_dir / "credentials.json"
        
        if creds_file.exists():
            logger.info("✅ Google credentials file already exists")
            return True
        
        # Create template credentials file
        template_creds = {
            "installed": {
                "client_id": "YOUR_CLIENT_ID.apps.googleusercontent.com",
                "project_id": "your-project-id",
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
                "client_secret": "YOUR_CLIENT_SECRET",
                "redirect_uris": ["urn:ietf:wg:oauth:2.0:oob", "http://localhost:8000"]
            }
        }
        
        with open(creds_file, 'w') as f:
            json.dump(template_creds, f, indent=2)
        
        logger.info("📝 Created Google credentials template")
        logger.warning("⚠️ Please replace template values with actual Google OAuth credentials")
        
        return True
    
    def test_installation(self):
        """Test the installation"""
        try:
            logger.info("🧪 Testing installation...")
            
            # Test Python imports
            test_imports = [
                "langchain",
                "langchain_openai",
                "langchain_community",
                "chromadb",
                "fastapi",
                "uvicorn"
            ]
            
            for module in test_imports:
                try:
                    __import__(module)
                    logger.info(f"✅ {module} import successful")
                except ImportError as e:
                    logger.error(f"❌ {module} import failed: {e}")
                    return False
            
            logger.info("✅ All core modules imported successfully")
            return True
            
        except Exception as e:
            logger.error(f"❌ Installation test failed: {e}")
            return False
    
    def run_setup(self, skip_deps=False):
        """Run the complete setup process"""
        logger.info("🚀 Starting Presidio Research Agent setup...")
        
        # Check Python version
        if not self.check_python_version():
            return False
        
        # Create directories
        if not self.create_directories():
            return False
        
        # Install dependencies
        if not skip_deps:
            if not self.install_python_dependencies():
                return False
            
            if not self.setup_node_dependencies():
                return False
        
        # Setup configuration
        if not self.setup_environment_file():
            return False
        
        if not self.setup_google_credentials():
            return False
        
        # Test installation
        if not skip_deps and not self.test_installation():
            return False
        
        logger.info("🎉 Setup completed successfully!")
        self.print_next_steps()
        
        return True
    
    def print_next_steps(self):
        """Print next steps for the user"""
        print("\n" + "="*60)
        print("🎯 NEXT STEPS")
        print("="*60)
        print()
        print("1. Configure your environment:")
        print(f"   Edit {self.env_file} and add your OpenAI API key")
        print()
        print("2. (Optional) Setup Google Docs integration:")
        print("   - Go to Google Cloud Console")
        print("   - Enable Google Docs & Drive APIs")
        print("   - Create OAuth 2.0 credentials")
        print(f"   - Replace template in {self.project_root}/data/google-docs-credentials/credentials.json")
        print()
        print("3. Start the agent:")
        print("   python agent-core/main.py")
        print()
        print("4. Or start the API server:")
        print("   python api_server.py")
        print("   Then visit http://localhost:8000/docs")
        print()
        print("5. Example queries to try:")
        print("   - 'What are our remote work policies?'")
        print("   - 'Find compliance policies related to AI data handling'")
        print("   - 'Compare our hiring trends with industry benchmarks'")
        print()
        print("="*60)

def main():
    """Main setup function"""
    parser = argparse.ArgumentParser(description="Setup Presidio Research Agent")
    parser.add_argument("--skip-deps", action="store_true", 
                       help="Skip dependency installation")
    parser.add_argument("--project-root", type=str,
                       help="Project root directory")
    
    args = parser.parse_args()
    
    setup = PresidioSetup(args.project_root)
    
    try:
        success = setup.run_setup(skip_deps=args.skip_deps)
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        logger.info("\n⚠️ Setup interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"❌ Setup failed with unexpected error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
