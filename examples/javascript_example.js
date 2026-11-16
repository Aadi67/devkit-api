
const BASE_URL = "http://127.0.0.1:8000";

async function generateUUIDs() {
    const response = await fetch(`${BASE_URL}/v1/uuid`, {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify({ count: 3 })
    });

    const result = await response.json();

    console.log(result);
}

generateUUIDs();
