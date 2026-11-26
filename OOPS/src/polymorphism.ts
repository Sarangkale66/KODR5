// polymorphism : poly(many) + morphism(forms)  --> "member function"

// type: 1. method overloading: same function name but differnet types of parameter
     //  2. method overriding

class Animal {
    hairColor:string = "";

    // member function
    setHairColor(newValue: string | number): void {
        if(typeof newValue === "string") {
            this.hairColor =  newValue;
        } else {
            const arr = ["black", "golden", "white"]; // 0 =< 3
            this.hairColor = arr[newValue] as string;
        }
    }

}

class Dog extends Animal {
    setHairColor(newValue: string | number): string| number {
        if(typeof newValue === "number")
            newValue = newValue + 2;
        else 
            newValue += "2"

        return newValue
    }
}

const d1 = new Dog();
d1.hairColor = "22333"
console.log(d1.setHairColor("21"), d1.hairColor);