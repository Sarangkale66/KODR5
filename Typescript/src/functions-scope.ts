// scope 


// @ts-ignore
// console.log(name);

//hositing

if(true) {
    let name = "sank" 
}
// console.log(name);


function helper() {
    var name = "sank"; // global scope && function scope
}

// console.log(name)

function greet(name:string){
  return "Hello, " + name;
}

const greet1 = (num:string) : number => {
    return Number(num);
}
                // callback
function result(call: (str:string)=> void) {
    call("sank 555");
}

// HOF
result((str:string) => {
    // console.log(str);
}) // refernce

// Default, Rest, and Spread Parameters

// Default
function hello(name:string="anil"):string {
    return "hii " + name;
}

hello();

// Rest
function video(num:number, num1:number, ...arr:number[]) {
    console.log(num, num1);
    console.log(arr);
    console.log(Array.isArray(arr));
}

// video(1,2,3,4,5,6,7,8)

function deep(arr:any):any {
    let newArr = []; // new reference
    for(let i=0; i<arr.length; i++) { // i = 1
        const elem = arr[i]; // [1,2,3,[1,2,3,[1,2,3,4,20],90],90]
        if(Array.isArray(elem)) {
            // new reference
            const result = deep(elem);
            newArr.push(result);
        } else { // primitive value
            newArr.push(elem);
        }

    }
    return newArr;
}

// Spread Operator
let arr:any[] = ["s",[1,2,3,[1,2,3,[1,2,3,4,20],90],90],"a",[1,2,3,4,90],"g"]; //xyz
let brr = deep(arr); // complete deep copy

// deep
brr[1][1] = 10
brr[1][3][1] = 22

console.dir(arr);
console.dir(brr, {depth:null});