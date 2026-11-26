//  type of data in js
// primitive (nnssbbu)
// reference [] {}

const arr:(number)[] = [10,20,30,40];

// arr.push(30);
// arr.pop();

// arr.unshift(5);
// const num = arr.shift();

// arr.splice(1,2);
// const num:number[] = arr.reverse();
// const num:number[] = arr.slice(1,3);

arr.forEach((elem, index, newArr)=> {
    // console.log(elem, index, newArr)
})

const result = arr.find((value:number,index:number, num:number[])=>{
    console.log(value, index, num);
    if(index === 3) return true;
})

console.log("value:", result);
