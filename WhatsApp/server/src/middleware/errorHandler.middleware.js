import { StatusCodes } from "http-status-codes"

const errorMiddleware = (err, req, res, next) => {
    const errMessage = err.message;
    const errName = err.name;
    const errStatus = err.statusCode || StatusCodes.INTERNAL_SERVER_ERROR;
    console.log(errMessage, errName, errStatus)
}

export default errorMiddleware;