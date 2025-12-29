import asyncio
import time

async def mock_process_topic(topic):
    print(f"Start processing {topic}")
    await asyncio.sleep(1) # Simulate network delay
    print(f"End processing {topic}")
    return topic

async def main():
    topics = ["Topic 1", "Topic 2", "Topic 3", "Topic 4", "Topic 5"]
    start_time = time.time()
    
    print("Starting concurrent execution test...")
    tasks = [mock_process_topic(topic) for topic in topics]
    await asyncio.gather(*tasks)
    
    end_time = time.time()
    duration = end_time - start_time
    
    print(f"\nTotal duration: {duration:.2f} seconds")
    if duration < 2.0:
        print("PASS: Execution was concurrent (took ~1s for 5x 1s tasks)")
    else:
        print("FAIL: Execution appeared sequential (took >2s)")

if __name__ == "__main__":
    asyncio.run(main())
