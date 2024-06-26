from flask import  Blueprint, request, jsonify, session, current_app, send_from_directory
import mysql.connector
from mysql.connector import Error
import connect
from werkzeug.security import generate_password_hash, check_password_hash
from flask_cors import CORS
from datetime import datetime
from werkzeug.utils import secure_filename
import os






user_blueprint = Blueprint('user', __name__)
CORS(user_blueprint)

def get_db_connection():
    return mysql.connector.connect(
        user=connect.dbuser,
        password=connect.dbpass,
        host=connect.dbhost,
        database=connect.dbname,
        autocommit=False
    )

def get_cursor(connection, dictionary_cursor=True):
    return connection.cursor(dictionary=dictionary_cursor)

@user_blueprint.route('/login', methods=['POST'])
def login():
    data = request.json
    connection = get_db_connection()
    try:
        cursor = get_cursor(connection, dictionary_cursor=True)
        cursor.execute('''
            SELECT u.UserID, u.Username, u.Password, u.Email, u.UserType, 
                   s.StudentID, s.EnrollmentYear, t.TeacherID, t.Title
            FROM Users u
            LEFT JOIN Students s ON u.UserID = s.UserID
            LEFT JOIN Teachers t ON u.UserID = t.UserID
            WHERE u.Email = %s
        ''', (data['email'],))
        user = cursor.fetchone()
        
        if user and check_password_hash(user['Password'], data['password']):
            # Set up the basic user info
            session['user_info'] = {
                "userId": user['UserID'],
                "username": user['Username'],
                "email": user['Email'],
                "userType": user['UserType']
            }
            # Add specific student or teacher info to session
            if user['UserType'] == 'student':
                session['user_info'].update({
                    "studentId": user['StudentID'],
                    "enrollmentYear": user['EnrollmentYear']
                })
            elif user['UserType'] == 'teacher':
                session['user_info'].update({
                    "teacherId": user['TeacherID'],
                    "title": user['Title']
                })
            # Prepare the response object
            user_info = session['user_info'].copy()
            user_info.update({"message": "Login successful"})
            return jsonify(user_info), 200
        else:
            return jsonify({"message": "Invalid email or password"}), 401
    except Error as e:
        return jsonify({"message": str(e)}), 500
    finally:
        if connection.is_connected():
            cursor.close()
            connection.close()

@user_blueprint.route('/logout')
def logout():
    session.clear()
    return jsonify({"message": "You have been logged out"}), 200

@user_blueprint.route('/update-profile', methods=['POST'])
def update_profile():
    data = request.json
    user_id = data.get('userId')
    
    if not user_id:
        return jsonify({"message": "User ID not provided"}), 400
    
    if not data.get('email') or not data.get('username'):
        return jsonify({"message": "Email and username cannot be empty"}), 400
    
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)
    try:
        cursor.execute("SELECT Password, UserType FROM Users WHERE UserID = %s", (user_id,))
        user = cursor.fetchone()
        if not user:
            return jsonify({"message": "User not found"}), 404

        if 'newPassword' in data and data['newPassword']:
            new_password_hashed = generate_password_hash(data['newPassword'])
            cursor.execute("UPDATE Users SET Password = %s WHERE UserID = %s", (new_password_hashed, user_id))

        cursor.execute("UPDATE Users SET Username = %s, Email = %s WHERE UserID = %s", (data['username'], data['email'], user_id))

      
        if 'enrollmentYear' in data:
            cursor.execute("UPDATE Students SET EnrollmentYear = %s WHERE UserID = %s", (data['enrollmentYear'], user_id))

       
        if user['UserType'] == 'teacher' and 'title' in data:
            cursor.execute("UPDATE Teachers SET Title = %s WHERE UserID = %s", (data['title'], user_id))

        connection.commit()
        
        cursor.execute("SELECT UserID, Username, Email, UserType FROM Users WHERE UserID = %s", (user_id,))
        updated_user = cursor.fetchone()
        
    
        session['user_info'] = {
            "userId": updated_user['UserID'],
            "username": updated_user['Username'],
            "email": updated_user['Email'],
            "userType": updated_user['UserType']
        }
        
        if updated_user['UserType'] == 'student':
            cursor.execute("SELECT EnrollmentYear FROM Students WHERE UserID = %s", (user_id,))
            student_info = cursor.fetchone()
            session['user_info']['enrollmentYear'] = student_info['EnrollmentYear']
        
        if updated_user['UserType'] == 'teacher':
            cursor.execute("SELECT Title FROM Teachers WHERE UserID = %s", (user_id,))
            teacher_info = cursor.fetchone()
            session['user_info']['title'] = teacher_info['Title']

        return jsonify(updated_user), 200

    except Exception as e:
        connection.rollback()
        return jsonify({"message": str(e)}), 500
    finally:
        cursor.close()
        connection.close()


@user_blueprint.route('/all-quizzes', methods=['GET'])
def get_all_quizzes():
    connection = get_db_connection()
    try:
        cursor = get_cursor(connection, dictionary_cursor=True)
        cursor.execute('''
            SELECT QuizID, QuizName, QuizImageURL 
            FROM Quizzes
        ''')
        quizzes = cursor.fetchall()
        return jsonify(quizzes), 200
    except Error as e:
        return jsonify({"message": str(e)}), 500
    finally:
        if connection.is_connected():
            cursor.close()
            connection.close()


@user_blueprint.route('/quiz/<int:quiz_id>/<int:student_id>', methods=['GET'])
def get_quiz_details(quiz_id, student_id):
    connection = get_db_connection()
    try:
        cursor = get_cursor(connection, dictionary_cursor=True)
        cursor.execute('''
            SELECT 
                q.QuizID, q.QuizName, q.QuizImageURL, q.SemesterID, 
                qi.QuestionID, qi.QuestionText, qi.QuestionType, qi.CorrectAnswer, 
                p.PlantID, p.LatinName, p.CommonName, pi.ImageURL,
                qo.OptionID, qo.OptionLabel, qo.OptionText, qo.IsCorrect
            FROM Quizzes q
            JOIN Questions qi ON qi.QuizID = q.QuizID
            LEFT JOIN PlantNames p ON qi.PlantID = p.PlantID
            LEFT JOIN PlantImages pi ON p.PlantID = pi.PlantID
            LEFT JOIN QuestionOptions qo ON qi.QuestionID = qo.QuestionID
            WHERE q.QuizID = %s
        ''', (quiz_id,))
        rows = cursor.fetchall()

        if rows:
            questions = {}
            for row in rows:
                if row['QuestionID'] not in questions:
                    questions[row['QuestionID']] = {
                        "questionId": row['QuestionID'],
                        "questionText": row['QuestionText'],
                        "questionType": row['QuestionType'],
                        "correctAnswer": row['CorrectAnswer'],
                        "plantId": row['PlantID'],
                        "latinName": row['LatinName'],
                        "commonName": row['CommonName'],
                        "imageUrl": row['ImageURL'],
                        "options": []
                    }
                if row['OptionID']:  # Ensure there is an option before adding it
                    questions[row['QuestionID']]['options'].append({
                        "optionId": row['OptionID'],
                        "optionLabel": row['OptionLabel'],
                        "optionText": row['OptionText'],
                        "isCorrect": row['IsCorrect']
                    })
            cursor.execute('''
                SELECT * FROM StudentQuizAnswers
                WHERE StudentID = %s AND QuizID = %s and ProgressID = (select Max(ProgressID) from StudentQuizAnswers where StudentID = %s AND QuizID = %s) 
            ''', (student_id, quiz_id, student_id, quiz_id))
            answers = cursor.fetchall()
            cursor.execute('''
                            SELECT count(*) as count FROM StudentQuizProgress
                            WHERE StudentID = %s AND QuizID = %s AND EndTimestamp is NULL
                        ''', (student_id, quiz_id))
            progressing = cursor.fetchone()
            connection.commit()

            response = {
                "progressing": progressing['count'] > 0,
                "quizId": quiz_id,
                "quizName": rows[0]['QuizName'],
                "quizImageUrl": rows[0]['QuizImageURL'],
                "questions": list(questions.values()),
                "answers": answers
            }
            return jsonify(response), 200
        else:
            return jsonify({"message": "Quiz not found"}), 404
    except Error as e:
        return jsonify({"message": str(e)}), 500
    finally:
        if connection.is_connected():
            cursor.close()
            connection.close()

@user_blueprint.route('/check-progress/<int:quiz_id>', methods=['GET'])
def check_progress(quiz_id):
    connection = get_db_connection()
    try:
        cursor = get_cursor(connection, dictionary_cursor=True)
        cursor.execute('''
            SELECT ProgressID, Score, EndTimestamp FROM StudentQuizProgress
            WHERE StudentID = %s AND QuizID = %s AND EndTimestamp IS NULL
        ''', (request.user.studentId, quiz_id))  # Assuming request.user is available with user's ID
        progress = cursor.fetchone()

        if progress:
            return jsonify({
                "progressId": progress['ProgressID'],
                "score": progress['Score'],
                "endTimestamp": progress['EndTimestamp']
            }), 200
        else:
            return jsonify({"message": "No active progress found"}), 404
    except Error as e:
        print("Database error:", str(e))
        return jsonify({"message": str(e)}), 500
    finally:
        if connection.is_connected():
            cursor.close()
            connection.close()

@user_blueprint.route('/save-progress/<int:quiz_id>', methods=['POST'])
def save_progress(quiz_id):
    data = request.json
    print("Received data:", data)  
    connection = get_db_connection()
    try:
        cursor = get_cursor(connection, dictionary_cursor=True)
        
        cursor.execute('''
            SELECT ProgressID, Score FROM StudentQuizProgress
            WHERE StudentID = %s AND QuizID = %s AND EndTimestamp IS NULL
        ''', (data['studentId'], quiz_id))
        progress = cursor.fetchone()

       
        if progress:
            progress_id = progress['ProgressID']
            current_score = progress.get('Score', 0) 
        else:
            
            cursor.execute('''
                INSERT INTO StudentQuizProgress (StudentID, QuizID, Score, StartTimestamp)
                VALUES (%s, %s, 0, NOW())
            ''', (data['studentId'], quiz_id))
            connection.commit()  # Commit the new progress record
            progress_id = cursor.lastrowid
            current_score = 0

        total_score = current_score

        for answer in data['answers']:
            selected_option_id = answer['selectedOptionId']  

            cursor.execute('''
    INSERT INTO StudentQuizAnswers (ProgressID, QuestionID, SelectedOptionId, IsCorrect, StudentId, QuizId)
    VALUES (%s, %s, %s, %s, %s, %s)
    ON DUPLICATE KEY UPDATE SelectedOptionId = VALUES(SelectedOptionId), IsCorrect = VALUES(IsCorrect)
''', (progress_id, answer['questionId'], selected_option_id, answer['isCorrect'], data['studentId'], quiz_id))
            
            if answer['isCorrect']:
                total_score += 1

        
        cursor.execute('''
            UPDATE StudentQuizProgress
            SET Score = %s
            WHERE ProgressID = %s
        ''', (total_score, progress_id))

        connection.commit()
        return jsonify({"message": "Progress saved successfully", "total_score": current_score}), 200
    except Error as e:
        connection.rollback()
        print("Database error:", str(e))
        return jsonify({"message": str(e)}), 500
    finally:
        if connection.is_connected():
            cursor.close()
            connection.close()
        print("Database connection closed.")

@user_blueprint.route('/submit-quiz/<int:quiz_id>', methods=['POST'])
def submit_quiz(quiz_id):
    data = request.json
    connection = get_db_connection()
    try:
        cursor = get_cursor(connection, dictionary_cursor=True)

        # Check for an existing, unfinished progress session
        cursor.execute('''
            SELECT ProgressID, Score FROM StudentQuizProgress
            WHERE StudentID = %s AND QuizID = %s AND EndTimestamp IS NULL
        ''', (data['studentId'], quiz_id))
        progress = cursor.fetchone()

        if progress:
            progress_id = progress['ProgressID']
            current_score = progress['Score']
            # Update the end time to close the session
            cursor.execute('''
                UPDATE StudentQuizProgress
                SET EndTimestamp = %s
                WHERE ProgressID = %s
            ''', (datetime.now(), progress_id))
        else:
            return jsonify({"message": "No active progress found to submit"}), 404

        connection.commit()
        return jsonify({"message": "Quiz submitted successfully", "final_score": current_score}), 200

    except Error as e:
        connection.rollback()
        return jsonify({"message": str(e)}), 500
    finally:
        if connection.is_connected():
            cursor.close()
            connection.close()

@user_blueprint.route('/progress-list', methods=['POST', 'GET'])
def get_progress_list():
    student_id = request.args.get('studentId')
    
    # 打印接收到的 studentId
    print(f"Received studentId: {student_id}")
    
    if not student_id:
        return jsonify({'message': 'Unauthorized access'}), 401

    connection = get_db_connection()
    try:
        cursor = get_cursor(connection)
        cursor.execute('''
            SELECT 
                p.ProgressID,
                q.QuizName,
                p.StartTimestamp
            FROM StudentQuizProgress p
            JOIN Quizzes q ON p.QuizID = q.QuizID
            WHERE p.StudentID = %s
        ''', (student_id,))
        progresses = cursor.fetchall()

        progress_list = [{
            'progressId': progress['ProgressID'],
            'quizName': progress['QuizName'],
            'startTimestamp': progress['StartTimestamp'].isoformat() if progress['StartTimestamp'] else None
        } for progress in progresses]

        return jsonify(progress_list), 200

    except Error as e:
        return jsonify({'message': str(e)}), 500
    finally:
        if connection.is_connected():
            cursor.close()
            connection.close()

@user_blueprint.route('/incorrect-answers/<int:progress_id>', methods=['GET'])
def get_incorrect_answers(progress_id):
    connection = get_db_connection()
    try:
        cursor = get_cursor(connection)
        cursor.execute('''
            SELECT 
                q.QuestionText, 
                a.SelectedOptionID, 
                q.CorrectAnswer,
                p.LatinName, 
                p.CommonName,
                q.QuestionID
            FROM StudentQuizAnswers a
            JOIN Questions q ON a.QuestionID = q.QuestionID
            JOIN PlantNames p ON q.PlantID = p.PlantID
            WHERE a.ProgressID = %s AND a.IsCorrect = 0
        ''', (progress_id,))
        answers = cursor.fetchall()
        
        # Process each answer to check if it's 'T', 'F' or an option ID
        for answer in answers:
            if answer['SelectedOptionID'] == 'T':
                answer['SelectedOption'] = 'True'
            elif answer['SelectedOptionID'] == 'F':
                answer['SelectedOption'] = 'False'
            else:
                # Retrieve the full option details if it's not 'T' or 'F'
                cursor.execute('''
                    SELECT OptionLabel, OptionText
                    FROM QuestionOptions
                    WHERE QuestionID = %s AND OptionID = %s
                ''', (answer['QuestionID'], answer['SelectedOptionID']))
                option_details = cursor.fetchone()
                if option_details:
                    answer['SelectedOption'] = f"{option_details['OptionLabel']}. {option_details['OptionText']}"
                else:
                    answer['SelectedOption'] = 'Unknown Option'

        return jsonify([{
            'questionText': ans['QuestionText'],
            'selectedOption': ans['SelectedOption'],
            'correctAnswer': ans['CorrectAnswer'],
            'latinName': ans['LatinName'],
            'commonName': ans['CommonName']
        } for ans in answers]), 200
    except Error as e:
        return jsonify({'message': str(e)}), 500
    finally:
        if connection.is_connected():
            cursor.close()
            connection.close()


@user_blueprint.route('/delete-progress/<int:progress_id>', methods=['DELETE'])
def delete_progress(progress_id):
    connection = get_db_connection()
    try:
        cursor = get_cursor(connection)
        # Delete associated answers first to maintain foreign key constraints
        cursor.execute('''
            DELETE FROM StudentQuizAnswers WHERE ProgressID = %s
        ''', (progress_id,))
        # Delete the progress record
        cursor.execute('''
            DELETE FROM StudentQuizProgress WHERE ProgressID = %s
        ''', (progress_id,))
        connection.commit()
        return jsonify({'message': 'Progress record deleted successfully'}), 200
    except Error as e:
        connection.rollback()
        return jsonify({'message': str(e)}), 500
    finally:
        if connection.is_connected():
            cursor.close()
            connection.close()

@user_blueprint.route('/score-rankings', methods=['GET'])
def get_score_rankings():
    connection = get_db_connection()
    try:
        cursor = get_cursor(connection)
        # Include only records where EndTimestamp is not NULL
        cursor.execute('''
            SELECT u.Username, p.Score, 
       TIMESTAMPDIFF(SECOND, p.StartTimestamp, p.EndTimestamp) as TimeTaken
    FROM StudentQuizProgress p
    JOIN Students s ON p.StudentID = s.StudentID
    JOIN Users u ON s.UserID = u.UserID
    WHERE p.EndTimestamp IS NOT NULL
    ORDER BY p.Score DESC, TimeTaken ASC;

        ''')
        rankings = cursor.fetchall()
        print(rankings) 
        return jsonify(rankings), 200
    except Error as e:
        return jsonify({'message': str(e)}), 500
    finally:
        if connection.is_connected():
            cursor.close()
            connection.close()

@user_blueprint.route('/edit-quiz/<int:quiz_id>', methods=['GET', 'POST'])
def edit_quiz(quiz_id):
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    if request.method == 'GET':
        try:
            cursor.execute('''
                SELECT 
                    q.QuizID, q.QuizName, q.QuizImageURL, q.SemesterID,
                    qi.QuestionID, qi.QuestionText, qi.QuestionType, qi.CorrectAnswer, qi.PlantID,
                    pn.LatinName, pn.CommonName,
                    pi.ImageID, pi.ImageURL
                FROM Quizzes q
                JOIN Questions qi ON q.QuizID = qi.QuizID
                LEFT JOIN PlantNames pn ON qi.PlantID = pn.PlantID
                LEFT JOIN PlantImages pi ON pn.PlantID = pi.PlantID
                WHERE q.QuizID = %s
            ''', (quiz_id,))
            quiz_details = cursor.fetchall()
            # print(quiz_details)

            # Modify the logic to handle both true_false and other question types correctly
            for question in quiz_details:
                if question['ImageURL']:
                    question['ImageURL'] = '/static/' + question['ImageURL']
                if question['QuestionType'] == 'true_false':
                    question['options'] = [
                        {"OptionID": None, "OptionText": "True", "IsCorrect": question['CorrectAnswer'] == "True"},
                        {"OptionID": None, "OptionText": "False", "IsCorrect": question['CorrectAnswer'] == "False"}
                    ]
                else:
                    cursor.execute('''
                        SELECT OptionID, OptionLabel, OptionText, IsCorrect
                        FROM QuestionOptions
                        WHERE QuestionID = %s
                    ''', (question['QuestionID'],))
                    question['options'] = cursor.fetchall()

            return jsonify(quiz_details), 200
        except Error as e:
            print(f"Database error: {str(e)}")
            return jsonify({"message": "Failed to retrieve quiz details"}), 500
        finally:
            cursor.close()
            connection.close()

    elif request.method == 'POST':
        data = request.json
        try:
            # Update Quiz details
            cursor.execute('''
                UPDATE Quizzes
                SET QuizName = %s, QuizImageURL = %s
                WHERE QuizID = %s
            ''', (data['quizName'], data['quizImageURL'], quiz_id))

            for question in data['questions']:
                # Update Questions
                cursor.execute('''
                    UPDATE Questions
                    SET QuestionText = %s, CorrectAnswer = %s
                    WHERE QuestionID = %s
                ''', (question['questionText'], question['correctAnswer'], question['questionId']))

                # Manage options
                if question['questionType'] == 'true_false':
                    # In a real scenario, you would handle the options update or creation here
                    pass
                else:
                    for option in question['options']:
                        cursor.execute('''
                            UPDATE QuestionOptions
                            SET OptionText = %s, IsCorrect = %s
                            WHERE OptionID = %s
                        ''', (option['optionText'], option['isCorrect'], option['optionId']))

            connection.commit()
            return jsonify({"message": "Quiz updated successfully"}), 200
        except Error as e:
            connection.rollback()
            print(f"Update error: {str(e)}")
            return jsonify({"message": "Failed to update quiz"}), 500
        finally:
            cursor.close()
            connection.close()

@user_blueprint.route('/upload-image/<int:question_id>', methods=['POST'])
def upload_image(question_id):
    if 'image' not in request.files:
        return jsonify({'message': 'No file part'}), 400

    file = request.files['image']
    if file.filename == '':
        return jsonify({'message': 'No selected file'}), 400

    filename = secure_filename(file.filename)
    
    filepath = os.path.join('plantpics', filename)
   
    full_server_path = os.path.abspath(os.path.join(current_app.root_path, '..', 'static', filepath))
    
    os.makedirs(os.path.dirname(full_server_path), exist_ok=True)
    
    file.save(full_server_path)
    print(full_server_path)  

    
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    try:
      
        cursor.execute("SELECT PlantID FROM Questions WHERE QuestionID = %s", (question_id,))
        plant_id_record = cursor.fetchone()
        if plant_id_record:
            plant_id = plant_id_record['PlantID']
         
            cursor.execute(
                "UPDATE PlantImages SET ImageURL = %s WHERE PlantID = %s",
                (filepath, plant_id)
            )
            connection.commit()
        else:
            return jsonify({'message': 'No plant associated with this question'}), 404

    except Exception as e:
        connection.rollback()
        print(f"Failed to update database: {str(e)}")
        return jsonify({'message': 'Database update failed'}), 500

    finally:
        cursor.close()

    return jsonify({'imageUrl': f'/static/{filepath}'}), 200
