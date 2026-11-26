# OOPS (java, js, ts, c++)
---> Class based Component

requirement
 --> strutured code
 --> modularity
 --> repeated code
 --> consistency
 --> extendable

## Class 
---> class is a blue print
---> class is wrapper which contains member variables and member function

```
class Animal {
    // member variable
    name: string

    // member function
    sound() {

    }
}

```

RAM memory --> stack , heap (new), --> new keyword aapko heap me create kiye hua variables ka address return karta hai

## Object
---> object is an instance of a class
instance: dynamic memory allocation ---> heap (new)

```
const a1 = new Animal(); // xyz (hexa decimal)
const a2 = new Animal(); // abc
```

- RAM suddenly increase

## constructor
-> is a class function which has no return type and use to initialize the member variable 

## this --> keyword
this -> Object of "current class"

--------- ✅ checkpoint ----------

## Access Modifier / Access Specifiers
A. Private: **✅ same class**, **❌ outside the class but inside same ".ts" file**, **❌ at different ".ts" file** 
B. Public:  **✅ same class**, **✅ outside the class but inside same ".ts" file**, **✅ at different ".ts" file** 
C. Protected:  **✅ same class**, **❌ outside the class but inside same ".ts" file**, **✅ at different ".ts" file(only within the child class)** 

# OOPS pillars: real life scenes ko code ke sath match krke dekhna padta hai

1. Encapsulation


2. Abstraction: 
   - Showing essential things and hiding unneccesary things, 
   - ✅ compulsion bithana hai 

   - abstraction kitne tarike se achieve kar sakte ho

--------- ✅ checkpoint ----------

3. Inheritance

- Types of Inheritance
    1. Is a Relation ----> direct connection with class batata hai 
        "extends"
        Example: Dog is an Animal // ✅
                 Animal is a Dog // ❌
    2. has a Relation
        Example: Animal has a Dog // ✅


4. Polymorphism


