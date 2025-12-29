import asyncio
import random
import re
from typing import Iterable, List, Set


HASHTAG_RE = re.compile(r"(?:^|\s)#([A-Za-z0-9_]+)")


def unique_preserve_order(items: Iterable[str]) -> List[str]:
	"""
	Remove duplicates from an iterable while preserving the original order.
	
	Args:
		items: Iterable of strings to deduplicate.
		
	Returns:
		Deduplicated list of strings.
	"""
	seen: Set[str] = set()
	ordered: List[str] = []
	for it in items:
		if it not in seen:
			seen.add(it)
			ordered.append(it)
	return ordered


def choose_user_agent(pool: List[str]) -> str:
	"""
	Choose a random user agent from a pool or return a default one.
	
	Args:
		pool: List of user agent strings.
		
	Returns:
		A selected user agent string.
	"""
	defaults = [
		"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
		"Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15",
		"Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
		"Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:122.0) Gecko/20100101 Firefox/122.0",
	]
	candidates = pool if pool else defaults
	return random.choice(candidates)


async def bounded_gather(semaphore: asyncio.Semaphore, coros: Iterable):
	"""
	Gather coroutines concurrently with a limit set by a semaphore.
	
	Args:
		semaphore: asyncio.Semaphore to control concurrency.
		coros: Iterable of coroutines.
	"""
	async def sem_task(coro):
		async with semaphore:
			return await coro
	return await asyncio.gather(*[sem_task(c) for c in coros], return_exceptions=True)


def extract_hashtags_from_text(text: str) -> List[str]:
	"""
	Extract hashtags from a given text using regex.
	
	Args:
		text: The input text to search for hashtags.
		
	Returns:
		List of extracted hashtags (without the # symbol).
	"""
	return [m.group(1) for m in HASHTAG_RE.finditer(text or "")]


