# Asset Portfolio System  

![OOP](https://img.shields.io/badge/Concept-OOP-blue)
![Inheritance](https://img.shields.io/badge/Design-3--Level%20Inheritance-success)
![Polymorphism](https://img.shields.io/badge/Principle-Polymorphism-orange)
![Encapsulation](https://img.shields.io/badge/Principle-Encapsulation-yellow)
![UML](https://img.shields.io/badge/Modeling-UML-lightgrey)


*OOP Design Showcase – 3-Level Inheritance Hierarchy*

This project demonstrates core Object-Oriented Programming principles*through a clean three-level class hierarchy modeling financial assets.  

It focuses on abstraction, inheritance, polymorphism, and encapsulation while maintaining a clear separation between equity-based and debt-based instruments.



---

## Design Summary

The system is structured around a base abstraction that represents a generic financial asset.  
From this root, the model branches into two intermediate categories:

- *Equity Assets*
- *Debt Assets*

Each category is further specialized into concrete asset types.


![Class Architecture](./docs/class_arch.png)


---

## Object-Oriented Principles Demonstrated

### Abstraction
A shared base type defines the common structure and behavior expected from all asset types.

### Inheritance
Specialized asset categories extend the base abstraction and introduce domain-specific attributes.

### Polymorphism
Each concrete asset provides its own implementation for risk evaluation and performance calculation while being treated uniformly at the portfolio level.

### Encapsulation
All internal state is managed through controlled access, ensuring modular and maintainable design.

---

## Conceptual Model

- *Asset*  
  Represents the minimal identity and shared behavior of all financial instruments.

- *EquityAsset*  
  Extends the base abstraction with price-based valuation attributes.

- *DebtAsset*  
  Extends the base abstraction with interest-based characteristics.

- *Stock & CryptoCurrency*  
  Equity instruments with volatility-driven risk models.

- *BankDeposit & Bond*  
  Debt instruments with structured return and interest-rate sensitivity models.

---

## Purpose of the Project

This project was built to demonstrate:

- Clean multi-level inheritance design
- Proper use of abstract behavior
- Runtime polymorphism
- Logical separation of financial domains
- Scalable and extendable class architecture

The structure allows new asset types to be added with minimal modification to existing code.