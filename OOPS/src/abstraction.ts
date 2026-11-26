// human.ts

export interface IHuman {
    getVoice: (tone:string) => string
}

export class Human implements IHuman {
    // member variable
    private _skinTone: string="";
    public name: string="";
    public voice:string = "";
    public type:string="";

    private getSkinTone() {
        return this._skinTone;
    }

    // bussiness logic
    getVoice(tone:string ):string {
        return this.voice + tone;
    }

    getName() {
        return this.name;
    }

    getType(): string {
        return this.type
    }
}

const h1 = new Human();
console.log(h1.name); 