CREATE TABLE user (
	id INT NOT NULL, 
	username VARCHAR(80) NOT NULL, 
	password_hash VARCHAR(128) NOT NULL, 
	is_admin BOOLEAN, 
	PRIMARY KEY (id), 
	UNIQUE (username)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE setting (
	`key` VARCHAR(64) NOT NULL, 
	value TEXT, 
	PRIMARY KEY (`key`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE job (
	id INT NOT NULL, 
	title VARCHAR(100) NOT NULL, 
	requirements TEXT, 
	description TEXT, 
	created_at DATETIME, 
	updated_at DATETIME, 
	user_id INT NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(user_id) REFERENCES user (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE resume (
	id INT NOT NULL, 
	filename VARCHAR(256) NOT NULL, 
	user_id INT NOT NULL, 
	size INT, 
	mtime DOUBLE, 
	analysis_status VARCHAR(32), 
	analysis_result TEXT, 
	job_id INT, 
	PRIMARY KEY (id), 
	FOREIGN KEY(user_id) REFERENCES user (id), 
	FOREIGN KEY(job_id) REFERENCES job (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE analysis_record (
	id INT NOT NULL, 
	resume_id INT NOT NULL, 
	user_id INT NOT NULL, 
	result TEXT, 
	status VARCHAR(32), 
	created_at DATETIME, 
	PRIMARY KEY (id), 
	FOREIGN KEY(resume_id) REFERENCES resume (id) ON DELETE CASCADE, 
	FOREIGN KEY(user_id) REFERENCES user (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

