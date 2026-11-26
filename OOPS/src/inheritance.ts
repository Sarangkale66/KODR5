// Is a Relation
    // 1. Single Inheritance
    // 2. Multiple Inheritance // ❌   has a Relation
    // 3. MultiLevel Inheritance
    // 4. Heirarchical Inheritance
    // 4. hybrid Inheritance 

class Animal {
    hairColor: string = "black"
}

class Breed {

}

class Dog  {

}

class Husky {
    // has a relation
   public animalObj: Animal = new Animal();
   public BreedObj: Breed = new Breed();
   public DogObj: Dog = new Dog();

   getHairColor() {
      return this.animalObj.hairColor;
   }
}


const h1 = new Husky();
console.log(h1.getHairColor());

// class class ----> extends
// interface interface ---> extends
// class interface ---> implements