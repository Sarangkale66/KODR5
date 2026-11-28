import UserRepo from "../../../repository/user.repository.js";

export default class AuthService {
    constructor() {
        const userRepository = new UserRepo();
    }
}