// Object: Interface && Types

interface IUser {
    readonly name?: string,
    age?: number,
    address: string[]
}

interface IObject {  
    addreage: number,
    ss: string[] 
}

type TStatus = "active" | "inactive";

// @ts-ignore
enum EStatus {
    "active" = 10,
    "inactive" = 20,
}

interface IEduction {
    arr:(string | number | boolean | IObject)[];
    education:{
        [key:string]: {
            yearOfPassing:string
        } | undefined
    },
    status: EStatus
}

const user: IUser & IEduction = {
    address: ["maharashtra", "madhya pradesh"],
    arr: ["riya", "ruchika", "etc", 10, 30, false, {  addreage: 21,ss: ["ramtek", "kamptee", "nagpur", "mansar"] }],
    education: {
        "ssc":{
            yearOfPassing: "2021"
        },
        "hsc": {
            yearOfPassing: "2022"
        },
        "graduation": {
            yearOfPassing: "2027"
        }
    },
    status: EStatus.active
}
// object change nahi kar paa rahe 
// Object.freeze(user)
// @ts-ignore
// user.name = "gourav"

const { name:fullname = "shubham", education: { ssc } } = user;

// delete user.education.ssc
user.education.ssc = undefined
// delete user.age 

console.log( fullname, ssc, user, user.education.ssc)
