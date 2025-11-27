The Gemini CV Ranking API is now fully deployed and ready for integration.

The core function is the POST endpoint at /rank, which accepts a Job Description and multiple CV files via multipart/form-data and returns a ranked list.

You can view the interactive documentation and schema details here: https://dina-tolba-cvparsingtask.hf.space/docs#/default/rank_candidates_rank_post

Key Integration Points:

The request must be sent as multipart/form-data with fields jd_file and cv_files.

The output match_score is a float percentage (0.00-100.00). Please display this value followed by a % sign on the front-end."

Note: I have uploaded for you 2 CVs and one JD file (Job Description) file for you incase you need to test using them.
