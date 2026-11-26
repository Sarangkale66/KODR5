import { Server } from "socket.io"

let myTurn = false; // "X" or "O"
let prevSocket = null;

export const setupSocketServer = (httpServer) => {
    const io = new Server(httpServer);

    io.on("connection", (socket)=>{
       socket.emit("my-symbol", {
            myTurn
       })
       myTurn = !myTurn // toogle
       if(prevSocket !== null){
            // room join kar denge
            const oldUser = prevSocket.id;
            const newUser = socket.id;

            let roomName = oldUser + newUser; // unique roomId
            console.log(roomName)
            socket.join(roomName)
            prevSocket.join(roomName)
            socket.to(roomName).emit("room-name", {roomN: roomName})
            prevSocket.to(roomName).emit("room-name", {roomN: roomName})
            prevSocket = null;
       }

       prevSocket = socket; // socket object

       socket.on("move", (data) => {
           const { roomName } = data
           console.log(data)
           socket.broadcast.to(roomName).emit("move", data)
       });

       socket.on('disconnect', () => {
            console.log('❌ User Disconnected:', socket.id);
       });
    })

}