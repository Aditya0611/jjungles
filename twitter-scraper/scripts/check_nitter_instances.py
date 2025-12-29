
import asyncio
import httpx
import logging
import sys
import time

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("nitter_checker")

# Potential Nitter instances to check
POTENTIAL_INSTANCES = [
    "https://nitter.net",
    "https://nitter.cz",
    "https://nitter.it",
    "https://nitter.unixfox.eu",
    "https://nitter.moomoo.me",
    "https://nitter.privacydev.net",
    "https://nitter.projectsegfau.lt",
    "https://nitter.eu",
    "https://nitter.soopy.moe",
    "https://nitter.rawbit.ninja",
    "https://nitter.kavin.rocks",
    "https://nitter.domain.glass",
    "https://nitter.1d4.us",
    "https://nitter.namazso.eu",
    "https://nitter.d420.de",
    "https://xcancel.com",
    "https://nitter.privacyredirect.com",
    "https://nitter.poast.org",
    "https://nitter.perplexonaut.com",
    "https://nitter.mint.lgbt",
    "https://nitter.esmailelbob.xyz",
    "https://nitter.dr460nef0rch.org",
    "https://nitter.lucabased.xyz",
    "https://nitter.salastil.com",
    "https://nitter.uni-sonia.com",
    "https://nitter.manasiwovi.github.io" 
]

TEST_QUERY = "Python"

async def check_instance(client, instance):
    url = f"{instance}/search/rss?f=tweets&q=%23{TEST_QUERY}"
    start_time = time.time()
    try:
        response = await client.get(url)
        elapsed = time.time() - start_time
        
        if response.status_code == 200:
            content_length = len(response.text)
            if "<item>" in response.text:
                logger.info(f"✅ SUCCESS: {instance} ({elapsed:.2f}s) - Found items")
                return instance, True, elapsed
            else:
                logger.warning(f"⚠️  EMPTY: {instance} ({elapsed:.2f}s) - 200 OK but no items (might be rate limited or empty)")
                return instance, False, elapsed
        elif response.status_code == 403:
             logger.error(f"❌ BLOCKED: {instance} ({elapsed:.2f}s) - 403 Forbidden")
             return instance, False, elapsed
        else:
            logger.error(f"❌ FAILED: {instance} ({elapsed:.2f}s) - Status {response.status_code}")
            return instance, False, elapsed
            
    except httpx.RequestError as e:
        logger.error(f"❌ ERROR: {instance} - {e}")
        return instance, False, 0
    except Exception as e:
        logger.error(f"❌ EXCEPTION: {instance} - {e}")
        return instance, False, 0

async def main():
    logger.info(f"Checking {len(POTENTIAL_INSTANCES)} Nitter instances...")
    
    working_instances = []
    
    async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
        tasks = [check_instance(client, instance) for instance in POTENTIAL_INSTANCES]
        results = await asyncio.gather(*tasks)
        
        for instance, is_working, elapsed in results:
            if is_working:
                working_instances.append(instance)
    
    logger.info("\n" + "="*50)
    logger.info(f"SUMMARY: Found {len(working_instances)} working instances")
    logger.info("="*50)
    for instance in working_instances:
        logger.info(f"🚀 {instance}")
        
    # Output list for easy copying
    print("\nPYTHON LIST:")
    print("NITTER_INSTANCES = [")
    for instance in working_instances:
        print(f'    "{instance}",')
    print("]")

if __name__ == "__main__":
    asyncio.run(main())
