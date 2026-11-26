// encapsulation: binding of data
//          : by making member variable as private and write it's respective getter and setters
// security
class Animal {
    // ✅
    private _type: string;
    private _name: string;
    private _age: number;

    constructor() {
        this._age = 10;
        this._name = "";
        this._type = "";
    }

    // setter
    set notYourType(newvalue:string) {
        if(typeof newvalue === "string") {
            this._type = newvalue;
        }
    }
    set name(newvalue:string) {
        this._name = newvalue;
    }
    set myAge(newvalue:number) {
        if(typeof newvalue === "number") {
            this._age = newvalue 
        }
    }

    // getter
    get name() {
        return this._name;
    }
    get type() {
        return this._type;
    }
    get myAge() {
        return this._age;
    }
}

const a1 = new Animal();
console.log(a1.myAge, a1.type)

// @ts-ignore
a1.myAge = null

// @ts-ignore
a1.type = "";

console.log(a1.myAge, a1.type)