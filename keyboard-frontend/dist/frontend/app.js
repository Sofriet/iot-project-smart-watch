const socket = new WebSocket("ws://localhost:8000/ws");


const keyboard = [
  [".","Q","W","E","R","T","Y","U","I","O","P","."],
  [".","A","S","D","F","G","H","J","K","L", "@","."],
  [".","?","Z","X","C","V","B","N","M",".",",","."]
];

let quadrant = 1;
let row = 1;
let col = 4;
let typed = "";

//figure this stuff out later 
const keyboardDiv = document.getElementById("keyboard");

function render() {
    keyboardDiv.innerHTML = "";

    for (let r = 0; r < keyboard.length; r++) {
        for (let c = 0; c < keyboard[r].length; c++) {

            const key = document.createElement("div");
            key.className = "key";

            // Which quadrant is this key in?
            const keyQuadrant = Math.floor(c / 3);

            // Highlight active quadrant
            if (keyQuadrant === quadrant) {
                key.classList.add("quadrant");
            }

            // Draw permanent quadrant boundaries
            if (c % 3 === 0) {
                key.classList.add("q-start");
            }

            if (c % 3 === 2) {
                key.classList.add("q-end");
            }

            // Highlight current key
            if (r === row && c === col) {
                key.classList.add("active");
            }

            key.innerText = keyboard[r][c];
            key.classList.add("selected");


            keyboardDiv.appendChild(key);
        }
    }

    document.getElementById("search-bar").value = typed;
}

render();


function handleCommand(cmd) {

    switch(cmd) {

        case "L_LEFT":
            col = Math.max(0, col - 1);
            break;

        case "L_RIGHT":
            col = Math.min(keyboard[0].length - 1, col + 1);
            break;

        case "L_UP":
            row = Math.max(0, row - 1);
            break;

        case "L_DOWN":
            row = Math.min(keyboard.length - 1, row + 1);
            break;

        case "Q_LEFT": //make these circular
            quadrant = (quadrant + 3) % 4;
            row = 1;
            col = Math.max(1, 3*quadrant - 1)
            break;

        case "Q_RIGHT"://make these circular
            quadrant = (quadrant + 1) % 4;
            row = 1;
            col = Math.min(keyboard[0].length - 2, 3*quadrant + 1)
            break;

        case "SELECT":
            typed += keyboard[row][col];
            break;

        case "SPACE":
            typed += " ";
            break;

        case "BACKSPACE":
            typed = typed.slice(0, -1);
            break;
    }

    render();
}

socket.onmessage = (event) => {
    const data = JSON.parse(event.data);
    handleCommand(data.action);
    console.log(`Received command: ${data.action}`);
};