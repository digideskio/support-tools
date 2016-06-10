package edu.babe.dedu;

import org.bson.types.ObjectId;
import org.springframework.data.annotation.Id;
import org.springframework.data.mongodb.core.mapping.Document;

@Document
public class Maycat {
	@Id
	private ObjectId id;

	private String fieldA;
	private int fieldB;

	public Maycat(String fieldA, int fieldB) {
		super();
		this.fieldA = fieldA;
		this.fieldB = fieldB;
	}

	@Override
	public String toString() {
		return "Maycat [id=" + id + ", fieldA=" + fieldA + ", fieldB=" + fieldB
				+ "]";
	}

	public String getFieldA() {
		return fieldA;
	}

	public int getFieldB() {
		return fieldB;
	}

	
}
