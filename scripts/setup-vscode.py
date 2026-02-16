#!/usr/bin/env python3
"""
Evo MCP Configuration Setup
Cross-platform script to configure the Evo MCP server for VS Code
"""

import json
import os
import platform
import sys
from pathlib import Path


class Colors:
    """ANSI color codes for terminal output"""
    BLUE = '\033[34m'
    GREEN = '\033[32m'
    RED = '\033[31m'
    RESET = '\033[0m'


def print_color(text: str, color: str = Colors.RESET):
    """Print colored text to terminal"""
    print(f"{color}{text}{Colors.RESET}")


def get_config_dir(variant: str | None = None) -> Path | None:
    """
    Get the VS Code configuration directory for the current platform.
    If variant is provided, use it; otherwise detect from environment or search.
    """
    system = platform.system()
    
    variants = ['Code', 'Code - Insiders']
    
    # If variant is provided, check only that one
    if variant:
        variants = [variant]
    
    if system == 'Windows':
        appdata = os.environ.get('APPDATA')
        if not appdata:
            return None
        
        for v in variants:
            config_dir = Path(appdata) / v / 'User'
            if config_dir.parent.exists():
                return config_dir
    
    elif system == 'Darwin':  # macOS
        home = Path.home()
        for v in variants:
            config_dir = home / 'Library' / 'Application Support' / v / 'User'
            if config_dir.parent.exists():
                return config_dir
    
    elif system == 'Linux':
        home = Path.home()
        for v in variants:
            config_dir = home / '.config' / v / 'User'
            if config_dir.parent.exists():
                return config_dir
    
    return None


def find_venv_python(project_dir: Path) -> Path | None:
    """Try to find a virtual environment in the project directory"""
    system = platform.system()
    venv_names = ['.venv', 'venv', 'env']
    
    for venv_name in venv_names:
        if system == 'Windows':
            python_path = project_dir / venv_name / 'Scripts' / 'python.exe'
        else:
            python_path = project_dir / venv_name / 'bin' / 'python'
        
        if python_path.exists():
            return python_path
    
    return None


def get_python_executable(project_dir: Path, is_workspace: bool) -> str:
    """
    Get the path to the Python executable.
    Uses the currently running Python interpreter, or tries to find a venv.
    """
    current_python = Path(sys.executable)
    
    if is_workspace:
        # For workspace config, try to use relative path if Python is in project
        try:
            rel_path = current_python.relative_to(project_dir)
            # Convert to forward slashes for cross-platform compatibility
            return './' + str(rel_path).replace('\\', '/')
        except ValueError:
            # Python is not in project directory, try to find a venv
            venv_python = find_venv_python(project_dir)
            if venv_python:
                try:
                    rel_path = venv_python.relative_to(project_dir)
                    return './' + str(rel_path).replace('\\', '/')
                except ValueError:
                    pass
            # Fall back to absolute path
            return str(current_python)
    else:
        # Use absolute path for user configuration
        return str(current_python)


def setup_mcp_config(config_type: str, variant: str | None = None):
    """
    Set up the MCP configuration for VS Code.
    
    Args:
        config_type: Either 'user' or 'workspace'
        variant: VS Code variant ('Code - Insiders' or 'Code'), only used for user config
    """
    print_color("Evo MCP Configuration Setup", Colors.BLUE)
    print("=" * 30)
    print()
    
    # Get the project directory (parent of scripts folder)
    script_dir = Path(__file__).parent.resolve()
    project_dir = script_dir.parent
    
    is_workspace = config_type == 'workspace'
    
    if is_workspace:
        # Workspace configuration
        config_dir = Path('.vscode')
        config_file = config_dir / 'mcp.json'
        print_color("Using workspace folder configuration", Colors.GREEN)
    else:
        # User configuration
        config_dir = get_config_dir(variant)
        
        if not config_dir:
            print_color(f"✗ Could not find {variant} installation directory", Colors.RED)
            sys.exit(1)
        
        config_file = config_dir / 'mcp.json'
        print_color(f"Using user configuration for {variant}", Colors.GREEN)
    
    print(f"Configuration file: {config_file}")
    print()
    
    # Ask which transport to use
    while True:
        print("Which transport would you like to use?")
        print("1. stdio - Local Python process (default)")
        print("2. sse - Network connection (for Docker or remote servers)")
        print()
        
        transport_choice = input("Enter your choice [1-2] (default: 1): ").strip()
        if not transport_choice:
            transport_choice = '1'
        
        if transport_choice in ['1', '2']:
            break
        
        print_color("Invalid choice. Please enter 1 or 2.", Colors.RED)
        print()
    
    print()
    use_sse = transport_choice == '2'
    
    # Get configuration based on transport type
    if use_sse:
        # SSE configuration
        print("Enter the MCP server URL details:")
        host = input("Host (default: localhost): ").strip() or "localhost"
        port = input("Port (default: 8000): ").strip() or "8000"
        
        server_config = {
            "type": "sse",
            "url": f"http://{host}:{port}/sse"
        }
        
        config_details = f"  URL: http://{host}:{port}/sse"
    else:
        # stdio configuration
        python_exe = get_python_executable(project_dir, is_workspace)
        if is_workspace:
            mcp_script = './src/mcp_tools.py'
        else:
            mcp_script = str(project_dir / 'src' / 'mcp_tools.py')
        
        server_config = {
            "type": "stdio",
            "command": python_exe,
            "args": [mcp_script]
        }
        
        config_details = f"  Command: {python_exe}\n  Script: {mcp_script}"
    
    print()
    
    # Create directory if it doesn't exist
    config_dir.mkdir(parents=True, exist_ok=True)
    
    # Read or create settings JSON
    if config_file.exists():
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                settings = json.load(f)
        except json.JSONDecodeError as e:
            print_color(f"✗ Invalid JSON in existing config file: {e}", Colors.RED)
            print(f"Please fix the syntax error in: {config_file}")
            sys.exit(1)
    else:
        settings = {}
    
    # Ensure servers exist
    if 'servers' not in settings:
        settings['servers'] = {}
    
    # Add or update the evo-mcp server configuration
    settings['servers']['evo-mcp'] = server_config
    
    # Write the updated settings to file
    try:
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(settings, f, indent=2)
        
        print_color("✓ Successfully added Evo MCP configuration", Colors.GREEN)
        print()
        print("Configuration details:")
        print(config_details)
        print()
        print("Next steps:")
        if use_sse:
            print("1. Start your MCP server with SSE transport enabled")
            print("   For Docker: docker-compose up -d")
            print("2. Restart VS Code or reload the window")
        else:
            print("Restart VS Code or reload the window")
            print()
            print("Note: This configuration uses the Python interpreter:")
            print(config_details.split('\n')[0].replace('  Command: ', '  '))
    except (IOError, OSError) as e:
        print_color(f"✗ Failed to update configuration file: {e}", Colors.RED)
        sys.exit(1)


def main():
    """Main entry point"""
    print_color("Evo MCP Configuration Setup", Colors.BLUE)
    print("=" * 30)
    print()
    
    # Ask which VS Code version
    try:
        while True:
            print("Which version of VS Code are you using?")
            print("1. VS Code (recommended)")
            print("2. VS Code Insiders")
            print()
            
            version_choice = input("Enter your choice [1-2] (default: 1): ").strip()
            if not version_choice:
                version_choice = '1'
            
            if version_choice in ['1', '2']:
                break
            
            print_color("Invalid choice. Please enter 1 or 2.", Colors.RED)
            print()
        
        variant = 'Code' if version_choice == '1' else 'Code - Insiders'
        print()
        
        # Ask where to add configuration
        while True:
            print("Where would you like to add the MCP server configuration?")
            print("1. User configuration (default)")
            print("2. Workspace folder configuration")
            print()
            
            choice = input("Enter your choice [1-2] (default: 1): ").strip()
            if not choice:
                choice = '1'
            
            if choice in ['1', '2']:
                break
            
            print_color("Invalid choice. Please enter 1 or 2.", Colors.RED)
            print()
        
        config_type = 'user' if choice == '1' else 'workspace'
        print()
        setup_mcp_config(config_type, variant if config_type == 'user' else None)
        
    except KeyboardInterrupt:
        print()
        print_color("Setup cancelled by user", Colors.RED)
        sys.exit(1)


if __name__ == '__main__':
    main()
