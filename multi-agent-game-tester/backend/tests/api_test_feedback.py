import asyncio
import httpx

BASE_URL = "http://localhost:8000/api"

async def submit_feedback(client, test_id, rating=5, comments="Great test"):
    params = {
        "rating": rating,
        "comments": comments
    }
    response = await client.post(f"{BASE_URL}/feedback/{test_id}", params=params)
    assert response.status_code == 200, f"Feedback submission failed: {response.text}"
    data = response.json()
    print(f"Feedback submitted for test_id {test_id}: {data['message']}")

async def main():
    async with httpx.AsyncClient() as client:
        # First generate tests and execute to get a test_id
        generate_payload = {
            "game_url": "http://example.com/game",
            "num_tests": 5,
            "select_top": 3
        }
        gen_resp = await client.post(f"{BASE_URL}/generate-tests", json=generate_payload)
        gen_data = gen_resp.json()
        session_id = gen_data["session_id"]

        # Rank and select
        rank_resp = await client.post(f"{BASE_URL}/rank-select/{session_id}", json={"num_selected": 3})
        assert rank_resp.status_code == 200

        # Execute tests
        exec_resp = await client.post(f"{BASE_URL}/execute-tests/{session_id}")
        assert exec_resp.status_code in (200, 202)

        # Wait for execution to complete
        await asyncio.sleep(12)

        # Get report to find test_ids
        report_resp = await client.get(f"{BASE_URL}/report/{session_id}")
        report_data = report_resp.json()
        test_results = report_data.get("test_results", [])

        if not test_results:
            print("No test results found to submit feedback")
            return

        # Submit feedback for first test
        first_test_id = test_results[0]["test_id"]
        await submit_feedback(client, first_test_id, rating=4, comments="Good test case")

if __name__ == "__main__":
    asyncio.run(main())
