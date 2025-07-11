from .server import serve


def main():
    """SmartCharge Helper PVPC - Smart charging time recommendations based on Spanish electricity prices (PVPC)"""
    import argparse
    import asyncio
    import sys

    parser = argparse.ArgumentParser(
        description="Smart electric car charging time advisor using Spanish PVPC electricity prices"
    )
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    
    args = parser.parse_args()
    
    try:
        asyncio.run(serve())
    except KeyboardInterrupt:
        print("\nShutdown complete")
        sys.exit(0)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
