import os
import json
import asyncio
from typing import Dict, Any, AsyncGenerator
from fastapi import FastAPI, HTTPException, Form, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from dotenv import load_dotenv
import tempfile
import shutil
import uuid
import numpy as np

from .appContext import AppContext
from .database.agent import callSQLAgent
from .spreadsheet.runSpreadsheetQuery import runSpreadSheetQuery
from .spreadsheet.loadPandasDF import loadPandasDF


class ChatRequest(BaseModel):
    message: str
    session_id: str = "default_session"


class ChatResponse(BaseModel):
    response: str
    status: str = "success"


class SpreadsheetResponse(BaseModel):
    response: str
    pandasCommand: str = ""
    status: str = "success"
    plotlyPlot: str = ""


class HealthResponse(BaseModel):
    status: str
    message: str


class JewelryChatbotAPI:
    def __init__(self):
        # Load environment variables
        if not load_dotenv():
            print("Warning: .env file not found, using environment variables")

        # Initialize the chatbot components with error handling
        print("Initializing Jewelry Chatbot API...")

        try:
            self.ctx = AppContext()
            self.is_initialized = True

            # The LangGraph workflow for chat is replaced by an agent.
            self.graph = None

            print("Jewelry Chatbot API initialized successfully!")

        except Exception as e:
            print(f"Warning: Failed to initialize chatbot with database: {str(e)}")
            print(
                "API will start in limited mode - database features will be unavailable"
            )
            self.ctx = None
            self.graph = None
            self.is_initialized = False

    def _check_initialization(self):
        """Check if the API is properly initialized with database connection"""
        if not self.is_initialized:
            raise HTTPException(
                status_code=503,
                detail="Service temporarily unavailable - database connection failed during startup",
            )

    async def process_chat_message(
        self, message: str, session_id: str
    ) -> Dict[str, Any]:
        """Process a chat message through the SQL Agent"""
        try:
            self._check_initialization()

            if not message or not message.strip():
                raise ValueError("Message cannot be empty")

            print(f"Processing message with agent: {message}")

            # Run the agent in a separate thread to avoid blocking the event loop
            agent_response = await asyncio.to_thread(
                callSQLAgent, self.ctx, message.strip(), session_id
            )
            answer = agent_response.get("answer", "")
            sql_query = agent_response.get("sql_query", "")

            return {"response": answer, "sqlQuery": sql_query, "status": "success"}

        except HTTPException:
            # Re-raise HTTP exceptions
            raise
        except Exception as e:
            print(f"Error processing message: {str(e)}")
            return {
                "response": f"I encountered an error while processing your request: {str(e)}",
                "status": "error",
            }

    async def stream_chat_message(
        self, message: str, session_id: str
    ) -> AsyncGenerator[str, None]:
        """Stream a chat message using the agent with fake real-time updates"""
        try:
            self._check_initialization()

            if not message or not message.strip():
                yield f"data: {json.dumps({'error': 'Message cannot be empty', 'status': 'error'})}\n\n"
                return

            print(f"Streaming message with agent: {message}")

            # IMMEDIATE RESPONSE - Start streaming right away
            yield f"data: {json.dumps({'response': 'Thinking...', 'status': 'analyzing'})}\n\n"
            await asyncio.sleep(0.01)

            # Run the agent in a separate thread to avoid blocking the event loop
            agent_response = await asyncio.to_thread(
                callSQLAgent, self.ctx, message.strip(), session_id
            )
            answer = agent_response.get("answer", "")
            sql_query = agent_response.get("sql_query", "")

            # Send the final response
            yield f"data: {json.dumps({'response': answer, 'sqlQuery': sql_query, 'status': 'completed'})}\n\n"

        except HTTPException as e:
            yield f"data: {json.dumps({'error': e.detail, 'status': 'error'})}\n\n"
        except Exception as e:
            print(f"Error streaming message: {str(e)}")
            yield f"data: {json.dumps({'error': f'I encountered an error: {str(e)}', 'status': 'error'})}\n\n"

    async def process_spreadsheet_message(
        self, message: str, file_path: str, session_id: str
    ) -> Dict[str, Any]:
        """Process a spreadsheet message through the spreadsheet analysis workflow"""
        try:
            self._check_initialization()

            if not message or not message.strip():
                raise ValueError("Message cannot be empty")

            if not file_path or not os.path.exists(file_path):
                raise ValueError("Valid file path is required")

            print(f"Processing spreadsheet message: {message}")
            print(f"File path: {file_path}")

            # Run the spreadsheet analysis
            result = runSpreadSheetQuery(
                message.strip(), file_path, self.ctx, session_id
            )

            if result is None:
                return {
                    "response": "I'm sorry, I couldn't process your spreadsheet request properly.",
                    "pandasCommand": "",
                    "status": "error",
                }

            # The result should contain the final step output
            answer = ""
            pandas_command = ""
            plotly_plot = "{}"

            # The result should contain the final step output
            for step_key, step_value in result.items():
                if "gen_answer" in step_key and step_value:
                    answer = step_value.get("answer", "")
                elif "gen_pandas_query" in step_key and step_value:
                    pandas_command = step_value.get("pandas_command", "")
                elif "gen_plot" in step_key and step_value:
                    plotly_plot = step_value.get("plotly_plot", "{}")

            if not answer:
                answer = (
                    "I processed your request but couldn't generate a proper response."
                )

            return {
                "response": answer,
                "pandasCommand": pandas_command,
                "status": "success",
                "plotlyPlot": plotly_plot,
            }

        except HTTPException:
            # Re-raise HTTP exceptions
            raise
        except Exception as e:
            print(f"Error processing spreadsheet message: {str(e)}")
            return {
                "response": f"I encountered an error while processing your spreadsheet: {str(e)}",
                "pandasCommand": "",
                "status": "error",
            }

    async def stream_spreadsheet_message(
        self, message: str, file_path: str, session_id: str
    ) -> AsyncGenerator[str, None]:
        """Stream a spreadsheet message through the analysis workflow with real-time updates"""
        try:
            self._check_initialization()

            if not message or not message.strip():
                yield f"data: {json.dumps({'error': 'Message cannot be empty', 'status': 'error'})}\n\n"
                return

            if not file_path or not os.path.exists(file_path):
                yield f"data: {json.dumps({'error': 'Valid file path is required', 'status': 'error'})}\n\n"
                return

            print(f"Streaming spreadsheet message: {message}")
            print(f"File path: {file_path}")

            # IMMEDIATE RESPONSE - Start streaming right away
            yield f"data: {json.dumps({'response': 'Loading your spreadsheet...', 'status': 'loading'})}\n\n"
            await asyncio.sleep(0.01)

            # Create a modified version of runSpreadSheetQuery that can stream
            from .spreadsheet.genPandasQuery import makeGenPandasQuery
            from .spreadsheet.execPandasQuery import makeExecPandasQuery
            from .spreadsheet.genAnswer import makeGenAnswer
            from .spreadsheet.genPlot import makeGenPlot
            from .utils.summarizeConversation import makeSummarizeConversation
            from langgraph.graph import START, StateGraph

            # Load the dataframe first
            df = loadPandasDF(file_path)
            yield f"data: {json.dumps({'response': 'Analyzing spreadsheet structure...', 'status': 'analyzing'})}\n\n"
            await asyncio.sleep(0.01)

            from .spreadsheet.state import State

            llm = self.ctx.llm

            graph_builder = StateGraph(State)
            graph_builder.add_node(
                "gen_pandas_query", makeGenPandasQuery(llm)
            )
            graph_builder.add_node("exec_pandas_query", makeExecPandasQuery())
            graph_builder.add_node("gen_answer", makeGenAnswer(llm))
            graph_builder.add_node("gen_plot", makeGenPlot(llm))
            graph_builder.add_node("summarize_conversation", makeSummarizeConversation(llm))

            graph_builder.set_entry_point("gen_pandas_query")
            graph_builder.add_edge("gen_pandas_query", "exec_pandas_query")
            graph_builder.add_edge("exec_pandas_query", "gen_answer")
            graph_builder.add_edge("gen_answer", "gen_plot")
            graph_builder.add_edge("gen_plot", "summarize_conversation")

            graph = graph_builder.compile(checkpointer=self.ctx.memory)

            config = {"configurable": {"thread_id": session_id}}

            # Stream status as we process each step
            step_count = 0
            pandas_command = ""
            final_answer = ""
            plotly_plot = "{}"

            # Helper function to convert numpy types to native Python types
            def convert_numpy_types(obj):
                if isinstance(obj, dict):
                    return {k: convert_numpy_types(v) for k, v in obj.items()}
                elif isinstance(obj, list):
                    return [convert_numpy_types(elem) for elem in obj]
                elif isinstance(obj, np.ndarray):
                    return obj.tolist()
                elif isinstance(obj, np.number):  # Covers all numpy numeric types (int, float, etc.)
                    return obj.item()
                return obj

            from langchain_core.messages import HumanMessage

            for step in graph.stream(
                {"question": message.strip(), "file_path": file_path, "chat_history": [HumanMessage(content=message.strip())]}, config
            ):
                step_count += 1

                # Stream different status messages for each step
                if "gen_pandas_query" in step:
                    yield f"data: {json.dumps({'response': 'Analyzing spreadsheet...', 'status': 'analyzing_spreadsheet'})}\n\n"
                    pandas_command = step["gen_pandas_query"].get("pandas_command", "")
                elif "exec_pandas_query" in step:
                    yield f"data: {json.dumps({'response': 'Executing pandas command...', 'status': 'executing_query'})}\n\n"
                elif "gen_answer" in step:
                    yield f"data: {json.dumps({'response': 'Generating final answer...', 'status': 'generating_answer'})}\n\n"
                    final_answer = step["gen_answer"].get("answer", "")
                elif "gen_plot" in step:
                    yield f"data: {json.dumps({'response': 'Generating plot...', 'status': 'generating_plot'})}\n\n"
                    plotly_plot = step["gen_plot"].get("plotly_plot", "{}")


                await asyncio.sleep(0.01)

            # Send the final response
            if not final_answer:
                final_answer = (
                    "I processed your request but couldn't generate a proper response."
                )
            
            # Convert any numpy types in the final response before serialization
            final_response_data = convert_numpy_types({'response': final_answer, 'pandasCommand': pandas_command, 'status': 'completed', 'plotlyPlot': plotly_plot})
            yield f"data: {json.dumps(final_response_data)}\n\n"

        except HTTPException as e:
            yield f"data: {json.dumps({'error': e.detail, 'status': 'error'})}\n\n"
        except Exception as e:
            print(f"Error streaming spreadsheet message: {str(e)}")
            yield f"data: {json.dumps({'error': f'I encountered an error: {str(e)}', 'status': 'error'})}\n\n"


# Initialize the chatbot API with error handling
chatbot_api = JewelryChatbotAPI()

# Create FastAPI app
app = FastAPI(
    title="Zivo Jewelry Chatbot API",
    description="FastAPI backend for the Zivo AI Jewelry Chatbot",
    version="1.0.0",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3000",
        "https://*.onrender.com",
        "https://*.render.com",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    try:
        if chatbot_api.is_initialized:
            return HealthResponse(
                status="healthy",
                message="Jewelry Chatbot API is running successfully with database connection",
            )
        else:
            return HealthResponse(
                status="degraded",
                message="Jewelry Chatbot API is running in limited mode - database connection failed",
            )
    except Exception as e:
        return HealthResponse(
            status="unhealthy",
            message=f"Jewelry Chatbot API encountered an error: {str(e)}",
        )


@app.post("/api/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest):
    """Main chat endpoint for processing user messages"""
    try:
        result = await chatbot_api.process_chat_message(
            request.message, request.session_id
        )
        return ChatResponse(**result)

    except Exception as e:
        print(f"API Error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@app.post("/api/chat/stream")
async def chat_stream_endpoint(request: ChatRequest):
    """Streaming chat endpoint for real-time responses using Server-Sent Events"""
    try:
        return StreamingResponse(
            chatbot_api.stream_chat_message(request.message, request.session_id),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",  # Disable nginx-level buffering
            },
        )

    except Exception as e:
        print(f"Streaming API Error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@app.post("/api/spreadsheet/upload")
async def upload_spreadsheet(file: UploadFile = File(...)):
    """Uploads a spreadsheet file and returns a file ID for subsequent use."""
    try:
        # Create a temporary directory for the session if it doesn't exist
        # This is a simple approach; for production, consider a more robust session management
        upload_dir = os.path.join(tempfile.gettempdir(), "spreadsheet_uploads")
        os.makedirs(upload_dir, exist_ok=True)

        # Save uploaded file to a temp file within the session directory
        suffix = os.path.splitext(file.filename)[-1]
        # Generate a unique filename to avoid collisions
        unique_filename = f"{uuid.uuid4()}{suffix}"
        file_path = os.path.join(upload_dir, unique_filename)

        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        return {"message": "File uploaded successfully", "file_id": file_path}

    except Exception as e:
        print(f"Spreadsheet upload API Error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@app.post("/api/spreadsheet/stream")
async def spreadsheet_stream_endpoint(
    message: str = Form(...),
    file_id: str = Form(None),
    session_id: str = Form("default_session"),
):
    """Streaming spreadsheet analysis endpoint for real-time responses using Server-Sent Events"""
    from starlette.background import BackgroundTask

    file_path = None
    try:
        if file_id:
            file_path = file_id
            if not os.path.exists(file_path):
                raise HTTPException(
                    status_code=404,
                    detail="File not found. Please upload the file again.",
                )
        else:
            raise HTTPException(status_code=400, detail="File ID is required.")

        def cleanup(path: str):
            # For now, we are not deleting the file after each request
            # as it's meant to be cached per session.
            # A more sophisticated cleanup mechanism (e.g., based on session expiry)
            # would be needed for production.
            pass

        cleanup_task = BackgroundTask(cleanup, path=file_path)

        return StreamingResponse(
            chatbot_api.stream_spreadsheet_message(message, file_path, session_id),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",  # Disable nginx-level buffering
            },
            background=cleanup_task,
        )

    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        print(f"Streaming Spreadsheet API Error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@app.post("/api/spreadsheet", response_model=SpreadsheetResponse)
async def spreadsheet_endpoint(
    message: str = Form(...),
    file_id: str = Form(None),
    session_id: str = Form("default_session"),
):
    """Spreadsheet analysis endpoint for processing user messages with a file ID."""
    file_path = None
    try:
        if file_id:
            file_path = file_id
            if not os.path.exists(file_path):
                raise HTTPException(
                    status_code=404,
                    detail="File not found. Please upload the file again.",
                )
        else:
            raise HTTPException(status_code=400, detail="File ID is required.")

        result = await chatbot_api.process_spreadsheet_message(
            message, file_path, session_id
        )
        return SpreadsheetResponse(**result)

    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        print(f"Spreadsheet API Error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@app.get("/")
async def root():
    """Root endpoint with API information"""
    try:
        status = "running" if chatbot_api.is_initialized else "limited"

        return {
            "message": "Zivo Jewelry Chatbot API",
            "version": "1.0.0",
            "status": status,
            "database_connected": chatbot_api.is_initialized,
            "endpoints": {
                "health": "/health",
                "chat": "/api/chat",
                "chat_stream": "/api/chat/stream",
                "spreadsheet": "/api/spreadsheet",
                "spreadsheet_stream": "/api/spreadsheet/stream",
                "docs": "/docs",
            },
        }
    except Exception as e:
        return {
            "message": "Zivo Jewelry Chatbot API",
            "version": "1.0.0",
            "status": "error",
            "error": str(e),
            "endpoints": {
                "health": "/health",
                "docs": "/docs",
            },
        }


if __name__ == "__main__":
    import uvicorn

    port = int(os.environ.get("PORT", 8000))
    host = os.environ.get("HOST", "0.0.0.0")

    print(f"Starting Zivo Jewelry Chatbot API server on {host}:{port}...")
    uvicorn.run("src.api:app", host=host, port=port, reload=False, log_level="info")
