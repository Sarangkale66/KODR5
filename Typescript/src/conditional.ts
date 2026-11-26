// if (5 == "5") {
//   console.log("Allowed, but risky");
// }

// never type
//    0 // 1 2 3 4 5 5 4 3 2 1
//    1 // 1 2 3 4 * * 4 3 2 1
//    2 // 1 2 3 * * * * 3 2 1
//    3 // 1 2 * * * * * * 2 1
//    4 // 1 * * * * * * * * 1
let n = 5; 


for(let i=0;i<5;i++){ // 2
    let str = "";
    for(let j =1; j<=n-i; j++){ // 3
        str += j + " "
    } 
    for(let k=0; k<2*i; k++) { // 2
        str += "* "
    } 
    for(let l=n-i; l>=1 ;l--) {
        str += l + " "
    }
    
    console.log(str); 
}                    
                      