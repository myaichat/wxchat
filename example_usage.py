#!/usr/bin/env python3
"""
Example usage of the imported send_message_with_streaming function
"""

from grok_cdp_pychrome_hybrid_generator import send_message_with_streaming, cleanup_connections

def example_usage():
    """Example of how to use the imported function"""
    
    # Example question
    question = "What is artificial intelligence?"
    
    print("🤖 Example: Using imported send_message_with_streaming function")
    print("=" * 60)
    print(f"❓ Question: {question}")
    print("=" * 60)
    
    try:
        # Use the imported function
        total_chunks = 0
        full_response = ""
        
        print("🔄 Starting streaming...")
        
        for chunk_info in send_message_with_streaming(question, timeout=60):
            total_chunks += 1
            
            if chunk_info.get('is_first'):
                print(f"📦 First chunk received ({chunk_info['chunk_size']} chars)")
                full_response = chunk_info['chunk']
                # Show first 200 characters
                preview = chunk_info['chunk'][:200] + "..." if len(chunk_info['chunk']) > 200 else chunk_info['chunk']
                print(f"Preview: {preview}")
                
            elif chunk_info.get('is_final'):
                print("🏁 Streaming complete!")
                break
                
            else:
                print(f"📦 Incremental chunk #{total_chunks}: {chunk_info['chunk_size']} chars")
                full_response += chunk_info['chunk']
        
        print(f"\n📊 Summary:")
        print(f"   Total chunks: {total_chunks}")
        print(f"   Final response length: {len(full_response)} characters")
        
        # Show final response (truncated)
        if full_response:
            print(f"\n🤖 Response preview:")
            print("-" * 40)
            preview = full_response[:500] + "..." if len(full_response) > 500 else full_response
            print(preview)
            print("-" * 40)
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        # Clean up connections
        cleanup_connections()
        print("\n✅ Cleanup completed!")

def show_function_info():
    """Show information about the imported function"""
    print("📋 Function Information:")
    print(f"   Name: {send_message_with_streaming.__name__}")
    print(f"   Doc: {send_message_with_streaming.__doc__}")
    print(f"   Module: {send_message_with_streaming.__module__}")
    
    # Show function signature
    import inspect
    sig = inspect.signature(send_message_with_streaming)
    print(f"   Signature: {send_message_with_streaming.__name__}{sig}")

if __name__ == "__main__":
    print("🚀 Grok CDP PyChrome Hybrid Generator - Import Example")
    print("=" * 60)
    
    # Show function info
    show_function_info()
    
    print("\n" + "=" * 60)
    print("💡 This example shows how to import and use the function.")
    print("⚠️  Note: This requires a running Chrome debug instance with Grok open.")
    print("   To actually run the streaming, uncomment the example_usage() call below.")
    print("=" * 60)
    
    # Uncomment the line below to run the actual example (requires Chrome debug instance)
    # example_usage()
    
    print("\n✅ Example completed!")
