#!/usr/bin/env python3
import asyncio
import websockets
import json

async def test_websocket():
    uri = "ws://localhost:8000/ws/aeb86895-a3f8-48fe-af89-97dbce02b541"

    try:
        async with websockets.connect(uri) as websocket:
            print("Connected to WebSocket")

            # Receive first 5 messages
            for i in range(5):
                message = await websocket.recv()
                data = json.loads(message)

                print(f"\n=== Message {i+1} ===")
                print(f"Type: {data.get('type')}")

                if 'data' in data:
                    cars = data['data'].get('cars', [])
                    print(f"Number of cars: {len(cars)}")

                    if cars:
                        print(f"\nFirst car:")
                        print(json.dumps(cars[0], indent=2))

                    metrics = data['data'].get('metrics', {})
                    print(f"\nMetrics:")
                    print(f"  Total arrivals: {metrics.get('total_arrivals')}")
                    print(f"  Total completions: {metrics.get('total_completions')}")
                    print(f"  Avg wait time: {metrics.get('average_wait_time')}")

                await asyncio.sleep(2)

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_websocket())
