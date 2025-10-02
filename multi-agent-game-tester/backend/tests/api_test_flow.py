import asyncio
import httpx

BASE_URL = "http://localhost:8000/api"

async def test_generate_tests(client):
    payload = {
        "game_url": "http://example.com/game",
        "num_tests": 20,
        "select_top": 10
    }
    response = await client.post(f"{BASE_URL}/generate-tests", json=payload)
    assert response.status_code == 200, f"Generate tests failed: {response.text}"
    data = response.json()
    assert "session_id" in data
    print("Generate tests passed")
    return data["session_id"]

async def test_rank_select(client, session_id):
    payload = {"num_selected": 10}
    response = await client.post(f"{BASE_URL}/rank-select/{session_id}", json=payload)
    assert response.status_code == 200, f"Rank & select failed: {response.text}"
    data = response.json()
    print("Rank & select passed")
    return session_id

async def test_execute_tests(client, session_id):
    response = await client.post(f"{BASE_URL}/execute-tests/{session_id}")
    assert response.status_code in (200, 202), f"Execute tests failed: {response.text}"
    data = response.json()
    print("Execute tests started")
    return session_id

async def test_get_report(client, session_id):
    response = await client.get(f"{BASE_URL}/report/{session_id}")
    assert response.status_code == 200, f"Get report failed: {response.text}"
    data = response.json()
    assert "execution_summary" in data
    print("Get report passed")

async def main():
    async with httpx.AsyncClient() as client:
        session_id = await test_generate_tests(client)
        session_id = await test_rank_select(client, session_id)
        session_id = await test_execute_tests(client, session_id)
        # Wait some time for execution to complete (mocked 10 seconds)
        import asyncio
        await asyncio.sleep(12)
        await test_get_report(client, session_id)

if __name__ == "__main__":
    asyncio.run(main())
