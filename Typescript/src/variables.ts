let node:null = null;
// let num:number = 1000;
// let str:string = "";
let symbol:symbol = Symbol("$");
let flag:boolean = false;
let bigValue:bigint = 1234567890n;
let name:undefined = undefined;

// unknown, any, never --> typescript


function append(str:string, b:number):string {
    str = "hii " + str;
    return str;
}

const ans = append("Anil ", 0)
console.log(ans);

// implicty TC
console.log("5" + 2); // "52" (number to string)
// console.log("5" - 2); // 3   (string to number)
// console.log(1 + true); // 2 (true becomes 1)

// String to Number
let str:string = "123";
let num = Number(str); // 123

// Number to String
let n = 456 as number;
let s = String(n); // "456"  

// Boolean to Number
let b = true;
let bn = Number(b); // 1

// String to Boolean
let bool = Boolean("hello"); // true
let empty = Boolean("");     // false

// truthy and falsy
// 0, null, none, "", undefine, document.all(), false ----> falsy
//  "mukesh", 1234, true, document.querySelector() --> truthy

// unknown vs any --> bypass
// unknown --> datatype check karo and then operation perform
// any --> sab aane 
let temp:any = null;

// unknown is way better than any
